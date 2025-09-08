from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from .models import User


class CustomUserCreationForm(forms.ModelForm):
    password1 = forms.CharField(label="Password", widget=forms.PasswordInput)
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput)

    class Meta:
        model = User
        fields = ("username", "fullname", "email", "phonenumber")

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        print("Password1:", password1)
        print("Password2:", password2)
        
        if password1 and password2 and password1 != password2:
            print("Passwords do not match!")
            raise forms.ValidationError("Passwords don't match")
        print("Passwords match.")
        return password2

    def save(self, commit=True):
        print("Saving user...")
        user = super().save(commit=False)
        print("Setting password...")
        user.set_password(self.cleaned_data["password1"])
        print("User saved.")
        if commit:
            print("Committing to database...")
            user.save()
            print("User committed.")
        print("Returning user...")
        return user


class CustomUserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ("username", "fullname", "email", "phonenumber", "password", "is_active", "is_staff")
