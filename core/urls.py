from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    
    # --- AUTENTICACIÓN ---
    path('accounts/login/', auth_views.LoginView.as_view(template_name='core/login.html'), name='login'),
    
    # AQUÍ ESTÁ EL CAMBIO: next_page='login' redirige al usuario al login tras salir
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),

    # --- PANTALLA PRINCIPAL ---
    path('', views.home, name='home'),

    # --- GESTIÓN DE USUARIOS (Solo Admin) ---
    path('usuarios/crear/', views.crear_empleado, name='crear_empleado'),
    
    # --- VENTAS ---
    path('venta/', views.crear_venta, name='crear_venta'),
    path('venta/ticket/<int:id_venta>/', views.ticket_venta, name='ticket_venta'),
    
    # --- INVENTARIO ---
    path('inventario/', views.lista_productos, name='lista_productos'),
    path('inventario/agregar/', views.agregar_producto, name='agregar_producto'),
    path('inventario/editar/<int:id_producto>/', views.editar_producto, name='editar_producto'),
    
    # --- CLIENTES ---
    path('clientes/', views.lista_clientes, name='lista_clientes'),
    
    # --- API ENDPOINTS (JSON) ---
    path('api/producto/<int:id_producto>/', views.obtener_producto, name='api_producto'),
    path('api/guardar-venta/', views.guardar_venta, name='api_guardar_venta'),
    path('api/clientes/buscar/', views.api_buscar_clientes, name='api_buscar_clientes'),
    path('api/clientes/crear/', views.api_crear_cliente, name='api_crear_cliente'),
    
    # --- CATEGORÍAS (ESTAS SON LAS QUE FALTABAN) ---
    path('categorias/', views.lista_categorias, name='lista_categorias'),
    path('categorias/agregar/', views.agregar_categoria, name='agregar_categoria'),
    path('categorias/editar/<int:id_categoria>/', views.editar_categoria, name='editar_categoria'),
]