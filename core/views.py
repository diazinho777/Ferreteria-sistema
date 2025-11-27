import json
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from .models import Producto, Venta, DetalleVenta, Cliente, Categoria, Proveedor, Compra, DetalleCompra
from .forms import ProductoForm, RegistroEmpleadoForm, CategoriaForm, ProveedorForm

# ==========================================
# 1. GESTIÓN DE ACCESO Y DASHBOARD
# ==========================================

@login_required
def home(request):
    """Panel principal (Dashboard)"""
    # SEGURIDAD: Si es empleado, no ve el dinero, va directo a vender
    if request.user.role == 'empleado':
        return redirect('crear_venta')

    hoy = timezone.now().date()
    
    # 1. Ventas de HOY
    ventas_hoy = Venta.objects.filter(fecha_venta__date=hoy)
    total_ventas_hoy = ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    cantidad_ventas_hoy = ventas_hoy.count()
    
    # 2. Productos con Stock Bajo (Menor o igual al mínimo)
    productos_bajo_stock = Producto.objects.filter(stock__lte=F('stock_minimo')).count()
    
    # 3. Últimas 5 ventas
    ultimas_ventas = Venta.objects.select_related('cliente').order_by('-fecha_venta')[:5]

    context = {
        'total_ventas_hoy': total_ventas_hoy,
        'cantidad_ventas_hoy': cantidad_ventas_hoy,
        'productos_bajo_stock': productos_bajo_stock,
        'ultimas_ventas': ultimas_ventas
    }
    return render(request, 'core/home.html', context)

@login_required
def crear_empleado(request):
    """Vista para que el Admin cree nuevos usuarios vendedores"""
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        # USAMOS EL NUEVO FORMULARIO
        form = RegistroEmpleadoForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.role = 'empleado' # Forzamos rol empleado
            user.save()
            return redirect('home')
    else:
        # USAMOS EL NUEVO FORMULARIO
        form = RegistroEmpleadoForm()
    
    return render(request, 'core/form_empleado.html', {
        'form': form
    })
# ==========================================
# 2. VISTAS DE VENTA (POS)
# ==========================================

@login_required
def crear_venta(request):
    """Renderiza la pantalla de venta"""
    return render(request, 'core/venta.html')

@login_required
def ticket_venta(request, id_venta):
    """Genera la vista para imprimir el ticket"""
    venta = get_object_or_404(Venta, id_venta=id_venta)
    detalles = venta.detalles.all()
    
    context = {
        'venta': venta,
        'detalles': detalles,
        'empresa': {
            'nombre': 'FERRETERÍA REDENTOR',
            'direccion': 'Calle Principal #123, Managua',
            'telefono': '2222-5555',
            'ruc': 'J031000000000'
        }
    }
    return render(request, 'core/ticket.html', context)

# ==========================================
# 3. INVENTARIO Y PRODUCTOS
# ==========================================

@login_required
def lista_productos(request):
    """Lista de productos (Visible para todos)"""
    busqueda = request.GET.get('q')
    productos = Producto.objects.all().order_by('nombre')

    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | 
            Q(id_producto__icontains=busqueda)
        )

    context = {
        'productos': productos,
        'busqueda': busqueda
    }
    return render(request, 'core/productos.html', context)

@login_required
def agregar_producto(request):
    """Crear producto nuevo"""
    # SEGURIDAD: Solo admin
    if request.user.role != 'admin':
        return redirect('lista_productos')

    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('lista_productos')
    else:
        form = ProductoForm()
    
    return render(request, 'core/form_producto.html', {'form': form, 'titulo': 'Nuevo Producto'})

@login_required
def editar_producto(request, id_producto):
    """Editar producto existente"""
    # SEGURIDAD: Solo admin
    if request.user.role != 'admin':
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    if request.method == 'POST':
        form = ProductoForm(request.POST, request.FILES, instance=producto)
        if form.is_valid():
            form.save()
            return redirect('lista_productos')
    else:
        form = ProductoForm(instance=producto)
    
    return render(request, 'core/form_producto.html', {'form': form, 'titulo': 'Editar Producto'})

# ==========================================
# 4. CLIENTES
# ==========================================

@login_required
def lista_clientes(request):
    """Directorio de clientes con estadísticas"""
    busqueda = request.GET.get('q')
    
    clientes = Cliente.objects.annotate(
        num_compras=Count('venta'),
        total_gastado=Sum('venta__total')
    ).order_by('-num_compras')

    if busqueda:
        clientes = clientes.filter(
            Q(nombres__icontains=busqueda) | 
            Q(cedula_ruc__icontains=busqueda)
        )

    context = {
        'clientes': clientes,
        'busqueda': busqueda
    }
    return render(request, 'core/clientes.html', context)

# ==========================================
# 5. APIs JSON (Backend para Alpine.js)
# ==========================================

@login_required
def obtener_producto(request, id_producto):
    try:
        producto = Producto.objects.get(id_producto=id_producto)
        data = {
            'encontrado': True,
            'id': producto.id_producto,
            'nombre': producto.nombre,
            'precio': float(producto.precio_venta),
            'stock': producto.stock
        }
    except Producto.DoesNotExist:
        data = {'encontrado': False}
    return JsonResponse(data)

@login_required
def api_buscar_clientes(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse([], safe=False)
    
    clientes = Cliente.objects.filter(
        Q(nombres__icontains=q) | 
        Q(cedula_ruc__icontains=q)
    )[:10]
    
    data = [{'id': c.id_cliente, 'text': str(c)} for c in clientes]
    return JsonResponse(data, safe=False)

@csrf_exempt
@login_required
def api_crear_cliente(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        try:
            nuevo_cliente = Cliente.objects.create(
                nombres=data.get('nombres'),
                cedula_ruc=data.get('cedula_ruc'),
                telefono=data.get('telefono'),
                email=data.get('email')
            )
            return JsonResponse({
                'status': 'ok',
                'cliente': {'id': nuevo_cliente.id_cliente, 'text': str(nuevo_cliente)}
            })
        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
    return JsonResponse({'status': 'error'})

@csrf_exempt
@login_required
def guardar_venta(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        items = data.get('items', [])
        total_venta = data.get('total', 0)
        id_cliente = data.get('id_cliente')

        if not items:
            return JsonResponse({'status': 'error', 'mensaje': 'El carrito está vacío'})

        try:
            with transaction.atomic():
                cliente_obj = None
                if id_cliente:
                    cliente_obj = Cliente.objects.get(id_cliente=id_cliente)

                nueva_venta = Venta.objects.create(
                    usuario=request.user,
                    cliente=cliente_obj,
                    total=total_venta
                )

                for item in items:
                    producto = Producto.objects.get(id_producto=item['id'])
                    if producto.stock < item['cantidad']:
                        raise Exception(f"Stock insuficiente para {producto.nombre}")

                    DetalleVenta.objects.create(
                        venta=nueva_venta,
                        producto=producto,
                        cantidad=item['cantidad'],
                        precio_unitario=item['precio'],
                        subtotal=item['precio'] * item['cantidad']
                    )
                    producto.stock -= item['cantidad']
                    producto.save()

            return JsonResponse({'status': 'ok', 'id_venta': nueva_venta.id_venta})

        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
            
    return JsonResponse({'status': 'error', 'mensaje': 'Método no permitido'})

# 6. GESTIÓN DE CATEGORÍAS (Solo Admin)
# ==========================================

@login_required
def lista_categorias(request):
    # SEGURIDAD: Solo admin
    if request.user.role != 'admin':
        return redirect('home')
        
    categorias = Categoria.objects.all().order_by('nombre')
    return render(request, 'core/lista_categorias.html', {'categorias': categorias})

@login_required
def agregar_categoria(request):
    if request.user.role != 'admin':
        return redirect('home')

    if request.method == 'POST':
        form = CategoriaForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm()
    
    return render(request, 'core/form_categoria.html', {'form': form, 'titulo': 'Nueva Categoría'})

@login_required
def editar_categoria(request, id_categoria):
    if request.user.role != 'admin':
        return redirect('home')
        
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)

    if request.method == 'POST':
        form = CategoriaForm(request.POST, instance=categoria)
        if form.is_valid():
            form.save()
            return redirect('lista_categorias')
    else:
        form = CategoriaForm(instance=categoria)
    
    return render(request, 'core/form_categoria.html', {'form': form, 'titulo': 'Editar Categoría'})

# 7. PROVEEDORES (Solo Admin)
# ==========================================
@login_required
def lista_proveedores(request):
    if request.user.role != 'admin': return redirect('home')
    proveedores = Proveedor.objects.all()
    return render(request, 'core/lista_proveedores.html', {'proveedores': proveedores})

@login_required
def agregar_proveedor(request):
    if request.user.role != 'admin': return redirect('home')
    if request.method == 'POST':
        form = ProveedorForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm()
    return render(request, 'core/form_proveedor.html', {'form': form, 'titulo': 'Nuevo Proveedor'})

# ==========================================
# 8. COMPRAS (ENTRADA DE STOCK)
# ==========================================
@login_required
def crear_compra(request):
    if request.user.role != 'admin': return redirect('home')
    proveedores = Proveedor.objects.all()
    return render(request, 'core/compra.html', {'proveedores': proveedores})

@csrf_exempt
@login_required
def guardar_compra(request):
    """Igual que venta, pero AUMENTA stock"""
    if request.method == 'POST':
        data = json.loads(request.body)
        items = data.get('items', [])
        total = data.get('total', 0)
        id_proveedor = data.get('id_proveedor')

        if not items or not id_proveedor:
            return JsonResponse({'status': 'error', 'mensaje': 'Datos incompletos'})

        try:
            with transaction.atomic():
                proveedor = Proveedor.objects.get(id_proveedor=id_proveedor)
                
                # 1. Crear Cabecera Compra
                nueva_compra = Compra.objects.create(
                    proveedor=proveedor,
                    usuario=request.user,
                    total=total
                )

                # 2. Detalles y AUMENTAR Stock
                for item in items:
                    producto = Producto.objects.get(id_producto=item['id'])
                    
                    DetalleCompra.objects.create(
                        compra=nueva_compra,
                        producto=producto,
                        cantidad=item['cantidad'],
                        costo_unitario=item['precio'], # Aquí es Precio de COSTO
                        subtotal=item['precio'] * item['cantidad']
                    )
                    
                    # AUMENTAMOS STOCK
                    producto.stock += item['cantidad']
                    # Actualizamos el costo del producto al nuevo precio de compra
                    producto.precio_compra = item['precio'] 
                    producto.save()

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
            
    return JsonResponse({'status': 'error'})