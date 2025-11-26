from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, Proveedor, Categoria, Producto, Compra, Venta, Cliente

# 1. Configuración para que el Usuario muestre el Rol
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ('username', 'first_name', 'last_name', 'role', 'cedula') # Agregamos nombre y cedula a la lista
    list_filter = ('role', 'is_staff')
    
    fieldsets = BaseUserAdmin.fieldsets + (
        # Agregamos los nuevos campos al detalle
        ('Información Personal', {'fields': ('role', 'cedula', 'telefono', 'direccion')}),
    )

# 2. Configuración para Productos
@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio_venta', 'stock', 'stock_minimo')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'id_producto')

# 3. Configuración para Ventas
@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('id_venta', 'usuario', 'cliente', 'fecha_venta', 'total')
    list_filter = ('fecha_venta',)
    date_hierarchy = 'fecha_venta'

# 4. Configuración para Clientes
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('nombres', 'cedula_ruc', 'telefono')
    search_fields = ('nombres', 'cedula_ruc')

# 5. Registros simples para el resto
admin.site.register(Proveedor)
admin.site.register(Categoria)
admin.site.register(Compra)