from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ["username", "email", "password1", "password2"]


class SingleUploadForm(forms.Form):
    docx_file = forms.FileField(
        label="Choose .docx file",
        help_text="Max 50MB",
    )
    use_transpect = forms.BooleanField(
        required=False,
        initial=True,
        label="Use transpect for MathType equations",
    )

    def clean_docx_file(self):
        f = self.cleaned_data["docx_file"]
        if not f.name.lower().endswith(".docx"):
            raise forms.ValidationError("Only .docx files are accepted.")
        if f.size > 50 * 1024 * 1024:
            raise forms.ValidationError("File size must be under 50 MB.")
        return f


class BatchUploadForm(forms.Form):
    docx_files = forms.FileField(
        label="Choose .docx files",
        widget=forms.ClearableFileInput(attrs={"allow_multiple_selected": True}),
    )
    use_transpect = forms.BooleanField(
        required=False,
        initial=True,
        label="Use transpect for MathType equations",
    )
