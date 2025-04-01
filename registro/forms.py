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
        fields = ['estudiante', 'justificacion']
        widgets = {
            'estudiante': forms.Select(attrs={'class': 'form-control'}),
            # 'curso': forms.Select(choices=CURSOS_CHILE, attrs={'class': 'form-control'}),
            'justificacion': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['estudiante'].widget.attrs['readonly'] = True
            # self.fields['curso'].widget.attrs['readonly'] = True
