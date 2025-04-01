from django import forms
from .models import Estudiante, Atraso, CURSOS_CHILE


class EstudianteForm(forms.ModelForm):
    class Meta:
        model = Estudiante
        fields = ['rut', 'nombre', 'curso', 'email1', 'email2']
        widgets = {
            'rut': forms.TextInput(attrs={'class': 'form-control'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'curso': forms.Select(choices=CURSOS_CHILE, attrs={'class': 'form-control'}),
            'email1': forms.EmailInput(attrs={'class': 'form-control'}),
            'email2': forms.EmailInput(attrs={'class': 'form-control'}),
        }


class AtrasoForm(forms.ModelForm):
    class Meta:
        model = Atraso
        fields = ['justificacion']  # Solo mostramos el campo de justificación
        widgets = {
            'justificacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    # Campo oculto para almacenar el ID del estudiante seleccionado
    estudiante_id = forms.CharField(widget=forms.HiddenInput(), required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['estudiante_id'].initial = self.instance.estudiante.id

    def clean_estudiante_id(self):
        # Asegurarse de que el ID del estudiante es válido
        estudiante_id = self.cleaned_data.get('estudiante_id')
        if estudiante_id:
            try:
                estudiante = Estudiante.objects.get(id=estudiante_id)
                return estudiante
            except Estudiante.DoesNotExist:
                raise forms.ValidationError("Estudiante no encontrado.")
        raise forms.ValidationError("Debe seleccionar un estudiante.")
