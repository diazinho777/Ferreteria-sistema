from django import forms
from django.contrib.auth.forms import UserCreationForm
from .models import Producto, User, Categoria, Proveedor

# 1. FORMULARIO DE PRODUCTOS (Para el Inventario)
class ProductoForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'categoria', 'precio_compra', 'precio_venta', 'stock', 'stock_minimo', 'imagen']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'categoria': forms.Select(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'precio_compra': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600', 'step': '0.01'}),
            'precio_venta': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600', 'step': '0.01'}),
            'stock': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600'}),
            'stock_minimo': forms.NumberInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600'}),
            'imagen': forms.ClearableFileInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded'}),
        }
        labels = {
            'stock_minimo': 'Alerta de Stock Mínimo',
            'precio_compra': 'Costo (Compra)',
            'precio_venta': 'Precio (Venta)',
        }

# 2. FORMULARIO DE EMPLEADOS (Modificado para quitar letras pequeñas y traducir)
class RegistroEmpleadoForm(UserCreationForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'cedula', 'telefono', 'direccion']
        
        widgets = {
            'username': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'placeholder': 'Usuario para entrar al sistema'}),
            'first_name': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'placeholder': 'Nombres'}),
            'last_name': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'placeholder': 'Apellidos'}),
            'cedula': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'placeholder': '000-000000-0000X'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'direccion': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'rows': 2}),
        }

    # --- AQUÍ ESTÁ LA MAGIA ---
    def __init__(self, *args, **kwargs):
        super(RegistroEmpleadoForm, self).__init__(*args, **kwargs)
        
        # 1. Quitar los textos de ayuda (letras pequeñas) de TODOS los campos
        for field_name in self.fields:
            self.fields[field_name].help_text = None

        # 2. Traducir Etiquetas Manualmente
        self.fields['username'].label = "Usuario"
        self.fields['first_name'].label = "Nombres"
        self.fields['last_name'].label = "Apellidos"
        self.fields['cedula'].label = "Cédula de Identidad"
        self.fields['telefono'].label = "Teléfono"
        self.fields['direccion'].label = "Dirección"
        
# 3. FORMULARIO DE CATEGORÍAS
class CategoriaForm(forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ['nombre', 'descripcion']
        
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'placeholder': 'Ej: Herramientas Eléctricas'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none', 'rows': 3, 'placeholder': 'Descripción opcional...'}),
        }
        
        
# 4. FORMULARIO DE PROVEEDORES
class ProveedorForm(forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ['empresa', 'ruc', 'direccion', 'telefono', 'email']
        widgets = {
            'empresa': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'ruc': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-2 border border-gray-300 rounded focus:border-red-600 focus:outline-none'}),
        }