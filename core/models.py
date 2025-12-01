from django.db import models
from django.contrib.auth.models import AbstractUser

# 1. USUARIOS
class User(AbstractUser):
    ROLES = (
        ('admin', 'Administrador'),
        ('empleado', 'Empleado'),
    )
    role = models.CharField(max_length=15, choices=ROLES, default='empleado', verbose_name="Rol")
    
    # --- NUEVOS CAMPOS ---
    cedula = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="Cédula de Identidad")
    telefono = models.CharField(max_length=15, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True, verbose_name="Dirección Domiciliar")

    class Meta:
        db_table = 'usuarios'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'

# 2. CATEGORÍAS
class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

    class Meta:
        db_table = 'categorias'
        verbose_name_plural = 'Categorías'

# 3. PROVEEDORES
class Proveedor(models.Model):
    id_proveedor = models.AutoField(primary_key=True)
    empresa = models.CharField(max_length=100)
    ruc = models.CharField(max_length=20, unique=True)
    email = models.EmailField(blank=True, null=True)
    telefono = models.CharField(max_length=20)
    direccion = models.TextField()

    def __str__(self):
        return self.empresa

    class Meta:
        db_table = 'proveedores'

# 4. PRODUCTOS
class Producto(models.Model):
    id_producto = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, db_column='id_categoria')
    precio_compra = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=5)
    activo = models.BooleanField(default=True, verbose_name="¿Activo?")
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    UNIDADES = (
        ('unidad', 'Unidad (Pza)'),
        ('metro', 'Metro (m)'),
        ('litro', 'Litro (L)'),
        ('galon', 'Galón (gal)'),
        ('libra', 'Libra (lb)'),
        ('kg', 'Kilogramo (kg)'),
        ('caja', 'Caja/Paquete'),
    )
    unidad = models.CharField(max_length=20, choices=UNIDADES, default='unidad', verbose_name="Unidad de Medida")

    def __str__(self):
        return f"ID: {self.id_producto} - {self.nombre}"

    class Meta:
        db_table = 'productos'

# 5. CLIENTES (NUEVA TABLA SIMPLIFICADA)
class Cliente(models.Model):
    id_cliente = models.AutoField(primary_key=True)
    nombres = models.CharField(max_length=100, verbose_name="Nombre Completo")
    cedula_ruc = models.CharField(max_length=20, blank=True, null=True, unique=True, verbose_name="Cédula/RUC")
    telefono = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    # Dirección ELIMINADA

    def __str__(self):
        return f"{self.nombres} ({self.cedula_ruc or 'S/C'})"

    class Meta:
        db_table = 'clientes'
        verbose_name_plural = 'Clientes'

# 6. COMPRAS
class Compra(models.Model):
    id_compra = models.AutoField(primary_key=True)
    proveedor = models.ForeignKey(Proveedor, on_delete=models.CASCADE, db_column='id_proveedor')
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, db_column='id_usuario')
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'compras'

class DetalleCompra(models.Model):
    id_detalle_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(Compra, related_name='detalles', on_delete=models.CASCADE, db_column='id_compra')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_column='id_producto')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.costo_unitario
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'detalle_compras'

# 7. VENTAS (ACTUALIZADA CON CLIENTE)
class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT, db_column='id_usuario')
    # Relación con la tabla Cliente
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, null=True, blank=True, db_column='id_cliente')
    
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    fecha_venta = models.DateTimeField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    class Meta:
        db_table = 'ventas'

class DetalleVenta(models.Model):
    id_detalle_venta = models.AutoField(primary_key=True)
    venta = models.ForeignKey(Venta, related_name='detalles', on_delete=models.CASCADE, db_column='id_venta')
    producto = models.ForeignKey(Producto, on_delete=models.PROTECT, db_column='id_producto')
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.subtotal = self.cantidad * self.precio_unitario
        super().save(*args, **kwargs)

    class Meta:
        db_table = 'detalle_ventas'
        
class Movimiento(models.Model):
    TIPOS = (
        ('entrada', 'Entrada (Compra)'),
        ('salida', 'Salida (Venta)'),
        ('ajuste_pos', 'Ajuste (+)'), # Por ejemplo, si encontraron stock perdido
        ('ajuste_neg', 'Ajuste (-)'), # Por ejemplo, si algo se rompió
    )
    
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    usuario = models.ForeignKey(User, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=20, choices=TIPOS)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    descripcion = models.CharField(max_length=255, blank=True) # Ej: "Venta #45"

    def __str__(self):
        return f"{self.tipo} - {self.producto.nombre} ({self.cantidad})"
    
    class Meta:
        db_table = 'movimientos'  
        verbose_name = 'Movimiento de Inventario'
        verbose_name_plural = 'Movimientos de Inventario'