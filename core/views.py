import json
import datetime
import decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.db import transaction
from django.db.models import Q, Count, Sum, F
from django.utils import timezone
from datetime import timedelta
from .models import Producto, Venta, DetalleVenta, Cliente, Categoria, Proveedor, Compra, DetalleCompra, User, Movimiento
from .forms import ProductoForm, RegistroEmpleadoForm, CategoriaForm, ProveedorForm, ClienteForm, EditarEmpleadoForm

# ==========================================
# 1. GESTIÓN DE ACCESO Y DASHBOARD
# ==========================================

@login_required
def home(request):
    """Panel principal (Dashboard)"""
    if request.user.role == 'empleado':
        return redirect('crear_venta')

    # 1. Rango de fecha
    ahora = timezone.localtime(timezone.now())
    inicio_dia = ahora.replace(hour=0, minute=0, second=0, microsecond=0)
    fin_dia = ahora.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # 2. Datos Generales
    ventas_hoy = Venta.objects.filter(fecha_venta__range=(inicio_dia, fin_dia))
    total_ventas_hoy = ventas_hoy.aggregate(Sum('total'))['total__sum'] or 0
    cantidad_ventas_hoy = ventas_hoy.count()
    productos_bajo_stock = Producto.objects.filter(stock__lte=F('stock_minimo')).count()
    
    # 3. Top 5 Productos
    top_productos = DetalleVenta.objects.values('producto__nombre') \
        .annotate(total_vendido=Sum('cantidad')) \
        .order_by('-total_vendido')[:5]

    # 4. Top 5 Clientes
    top_clientes = Cliente.objects.annotate(
        num_compras=Count('venta')
    ).order_by('-num_compras')[:5]

    # 5. NUEVO: Top Empleados (Por dinero vendido)
    # Filtramos usuarios que tengan al menos una venta para no llenar la lista de ceros
    top_empleados = User.objects.filter(venta__isnull=False).annotate(
        dinero_vendido=Sum('venta__total'),
        cantidad_ventas=Count('venta')
    ).order_by('-dinero_vendido')[:5]

    # 6. Últimas ventas
    ultimas_ventas = Venta.objects.select_related('cliente').order_by('-fecha_venta')[:5]

    context = {
        'total_ventas_hoy': total_ventas_hoy,
        'cantidad_ventas_hoy': cantidad_ventas_hoy,
        'productos_bajo_stock': productos_bajo_stock,
        'ultimas_ventas': ultimas_ventas,
        'top_productos': top_productos,
        'top_clientes': top_clientes,
        'top_empleados': top_empleados # Variable nueva
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
            'nombre': 'FERRETERÍA MI REDENTOR',
            'direccion': 'Ciudad Sandino, Managua',
            'telefono': '2222-5555',
            'ruc': 'J031000000000'
        }
    }
    return render(request, 'core/ticket.html', context)

# ==========================================
# 3. INVENTARIO Y PRODUCTOS
# ==========================================

# Modifica esta función existente
@login_required
def lista_productos(request):
    busqueda = request.GET.get('q')
    estado = request.GET.get('estado')
    categoria_id = request.GET.get('categoria') # <--- NUEVO: Filtro
    
    # 1. Filtro de Estado (Activo/Papelera)
    if estado == 'inactivos':
        productos = Producto.objects.filter(activo=False)
    else:
        productos = Producto.objects.filter(activo=True)

    # 2. Filtro por Categoría (NUEVO)
    if categoria_id:
        productos = productos.filter(categoria_id=categoria_id)

    # 3. Buscador
    if busqueda:
        productos = productos.filter(
            Q(nombre__icontains=busqueda) | 
            Q(id_producto__icontains=busqueda)
        )
    
    # 4. ORDENAMIENTO POR ID (NUEVO)
    productos = productos.order_by('id_producto')

    # Obtenemos todas las categorías para el dropdown
    categorias = Categoria.objects.all().order_by('nombre')

    context = {
        'productos': productos,
        'busqueda': busqueda,
        'estado': estado,
        'categorias': categorias,       # Enviamos la lista
        'categoria_seleccionada': int(categoria_id) if categoria_id else None
    }
    return render(request, 'core/productos.html', context)

# Agrega esta NUEVA función al final
@login_required
def activar_producto(request, id_producto):
    if request.user.role != 'admin':
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    producto.activo = True
    producto.save()
    return redirect('lista_productos')


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
        producto = Producto.objects.get(id_producto=id_producto, activo=True)
        data = {
            'encontrado': True,
            'id': producto.id_producto,
            'nombre': producto.nombre,
            # Forzamos conversión a float para evitar problemas con Decimal
            'precio': float(producto.precio_venta),
            'stock': float(producto.stock),
            'unidad': producto.get_unidad_display() # Opcional: Para mostrar la unidad si quieres
        }
    except Producto.DoesNotExist:
        data = {'encontrado': False}
    except Exception as e:
        # Esto nos ayudará a ver si hay otro error en la consola del servidor
        print(f"Error en obtener_producto: {e}") 
        data = {'encontrado': False}
        
    return JsonResponse(data)

@login_required
def eliminar_producto(request, id_producto):
    # SEGURIDAD: Solo admin
    if request.user.role != 'admin':
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)
    
    if request.method == 'POST':
        # BORRADO LÓGICO
        producto.activo = False
        producto.save()
        return redirect('lista_productos')
    
    return render(request, 'core/confirmar_eliminar.html', {'producto': producto})

@login_required
def api_buscar_clientes(request):
    q = request.GET.get('q', '')
    if len(q) < 2:
        return JsonResponse([], safe=False)
    
    # RECUERDA: Si usaste cedula_ruc, cambialo aqui. Si es cedula, dejalo asi.
    clientes = Cliente.objects.filter(
        Q(nombres__icontains=q) | 
        Q(cedula_ruc__icontains=q) 
    )[:10]
    
    # AQUI AGREGAMOS LA LOGICA VIP
    data = []
    for c in clientes:
        num_compras = c.venta_set.count() # Contamos sus ventas
        es_vip = num_compras > 5          # Si tiene más de 5, es VIP
        data.append({
            'id': c.id_cliente, 
            'text': str(c),
            'es_vip': es_vip,             # Enviamos este dato al frontend
            'num_compras': num_compras
        })
        
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
        descuento = data.get('descuento', 0) # <--- RECIBIMOS EL DESCUENTO

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
                    total=total_venta,
                    descuento=descuento # <--- GUARDAMOS EL DESCUENTO
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
                    
                    Movimiento.objects.create(
                        producto=producto,
                        usuario=request.user,
                        tipo='salida',
                        cantidad=item['cantidad'],
                        descripcion=f"Venta #{nueva_venta.id_venta}")

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
                    
                    Movimiento.objects.create(
                        producto=producto,
                        usuario=request.user,
                        tipo='entrada',
                        cantidad=item['cantidad'],
                        descripcion=f"Compra a {proveedor.empresa}")

            return JsonResponse({'status': 'ok'})

        except Exception as e:
            return JsonResponse({'status': 'error', 'mensaje': str(e)})
            
    return JsonResponse({'status': 'error'})

@login_required
def reporte_financiero(request):
    # SEGURIDAD: Solo admin
    if request.user.role != 'admin':
        return redirect('home')

    # 1. Obtener fechas del filtro (o usar mes actual por defecto)
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    hoy = timezone.localtime(timezone.now())

    if not fecha_inicio:
        # Por defecto: Primer día del mes actual
        fecha_inicio = hoy.replace(day=1).strftime('%Y-%m-%d')
    
    if not fecha_fin:
        # Por defecto: Hoy
        fecha_fin = hoy.strftime('%Y-%m-%d')

    # 2. Filtrar Ventas (Convertimos string a objeto fecha para hacer range)
    # Agregamos horas para cubrir el día completo final (23:59:59)
    f_ini = datetime.datetime.strptime(fecha_inicio, '%Y-%m-%d')
    f_fin = datetime.datetime.strptime(fecha_fin, '%Y-%m-%d') + datetime.timedelta(days=1) - datetime.timedelta(seconds=1)

    ventas = Venta.objects.filter(fecha_venta__range=(f_ini, f_fin)).order_by('-fecha_venta')

    # 3. Cálculos Financieros
    total_ingresos = ventas.aggregate(Sum('total'))['total__sum'] or 0
    
    # Calcular Ganancia Estimada:
    # (Esto es complejo porque el costo cambia, haremos una aproximación con el costo ACTUAL del producto)
    ganancia_bruta = 0
    for v in ventas:
        for detalle in v.detalles.all():
            # Ingreso por este producto en esta venta
            ingreso_item = detalle.subtotal 
            # Costo estimado (Cantidad * Costo actual del producto)
            costo_item = detalle.cantidad * detalle.producto.precio_compra
            ganancia_bruta += (ingreso_item - costo_item)

    # Restar descuentos globales si aplicaste descuento al total de la venta
    total_descuentos = ventas.aggregate(Sum('descuento'))['descuento__sum'] or 0
    # La ganancia real se ve afectada por el descuento que diste
    ganancia_neta = ganancia_bruta - total_descuentos

    context = {
        'ventas': ventas,
        'total_ingresos': total_ingresos,
        'ganancia_estimada': ganancia_neta,
        'total_descuentos': total_descuentos,
        'fecha_inicio': fecha_inicio,
        'fecha_fin': fecha_fin
    }
    return render(request, 'core/financiero.html', context)

@login_required
def historial_producto(request, id_producto):
    producto = get_object_or_404(Producto, id_producto=id_producto)
    movimientos = Movimiento.objects.filter(producto=producto).order_by('-fecha')
    return render(request, 'core/historial.html', {'producto': producto, 'movimientos': movimientos})

@login_required
def reportar_perdida(request, id_producto):
    # SEGURIDAD: Solo admin debería poder dar de baja inventario
    if request.user.role != 'admin':
        return redirect('lista_productos')

    producto = get_object_or_404(Producto, id_producto=id_producto)

    if request.method == 'POST':
        cantidad = float(request.POST.get('cantidad'))
        motivo = request.POST.get('motivo')

        if cantidad > 0:
            with transaction.atomic():
                # 1. Registrar en Kardex (Ajuste Negativo)
                Movimiento.objects.create(
                    producto=producto,
                    usuario=request.user,
                    tipo='ajuste_neg', # Tipo que definimos antes en models
                    cantidad=cantidad,
                    descripcion=f"PÉRDIDA: {motivo}"
                )

                # 2. Restar del Stock
                producto.stock -=  decimal.Decimal(cantidad) # Asegúrate de importar decimal si hace falta
                producto.save()
            
            return redirect('historial_producto', id_producto=producto.id_producto)

    return render(request, 'core/form_perdida.html', {'producto': producto})

@login_required
def editar_cliente(request, id_cliente):
    # Nota: No restringimos a admin porque un empleado podría corregir un teléfono
    cliente = get_object_or_404(Cliente, id_cliente=id_cliente)
    
    # Creamos un formulario rápido solo para esto (o reusamos uno genérico)
    # Como no tenemos un ClienteForm explícito en forms.py, lo creamos al vuelo con modelform_factory
    # O mejor, lo agregamos a forms.py para hacerlo bien.
    pass # (Ver paso siguiente)

@login_required
def editar_cliente(request, id_cliente):
    cliente = get_object_or_404(Cliente, id_cliente=id_cliente)
    
    if request.method == 'POST':
        form = ClienteForm(request.POST, instance=cliente)
        if form.is_valid():
            form.save()
            return redirect('lista_clientes')
    else:
        form = ClienteForm(instance=cliente)
        
    # Reusamos la plantilla de formulario de proveedor/categoria para ahorrar código
    return render(request, 'core/form_generico.html', {'form': form, 'titulo': 'Editar Cliente', 'atras': 'lista_clientes'})

@login_required
def editar_proveedor(request, id_proveedor):
    if request.user.role != 'admin': return redirect('home')
    
    proveedor = get_object_or_404(Proveedor, id_proveedor=id_proveedor)
    
    if request.method == 'POST':
        form = ProveedorForm(request.POST, instance=proveedor)
        if form.is_valid():
            form.save()
            return redirect('lista_proveedores')
    else:
        form = ProveedorForm(instance=proveedor)
        
    return render(request, 'core/form_generico.html', {'form': form, 'titulo': 'Editar Proveedor', 'atras': 'lista_proveedores'})

# 9. GESTIÓN DE EMPLEADOS (LISTA Y EDICIÓN)
# ==========================================

@login_required
def lista_empleados(request):
    # Solo admin
    if request.user.role != 'admin': return redirect('home')
    
    # Traemos a todos EXCEPTO al superusuario para no editarse a sí mismo por error
    empleados = User.objects.exclude(is_superuser=True).order_by('username')
    
    return render(request, 'core/lista_empleados.html', {'empleados': empleados})

@login_required
def editar_empleado(request, id_usuario):
    if request.user.role != 'admin': return redirect('home')
    
    empleado = get_object_or_404(User, pk=id_usuario)
    
    if request.method == 'POST':
        form = EditarEmpleadoForm(request.POST, instance=empleado)
        if form.is_valid():
            form.save()
            return redirect('lista_empleados')
    else:
        form = EditarEmpleadoForm(instance=empleado)
        
    return render(request, 'core/form_generico.html', {
        'form': form, 
        'titulo': f'Editar a {empleado.username}',
        'atras': 'lista_empleados'
    })

@login_required
def estado_empleado(request, id_usuario):
    """Activa o Desactiva el acceso al sistema"""
    if request.user.role != 'admin': return redirect('home')
    
    empleado = get_object_or_404(User, pk=id_usuario)
    # Invertimos el estado: Si es True pasa a False, y viceversa
    empleado.is_active = not empleado.is_active
    empleado.save()
    
    return redirect('lista_empleados')