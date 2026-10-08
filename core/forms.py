from django import forms


class ForgotPasswordForm(forms.Form):

    identifier = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'placeholder':
                    'Enter your registered email or mobile number'
            }
        )
    )

    reset_method = forms.ChoiceField(
        choices=[
            ('email', 'Email'),
            ('mobile', 'Mobile Number'),
        ],
        widget=forms.RadioSelect
    )


# ==========================================================
# REGISTER FORM
# ==========================================================

class RegisterForm(forms.Form):

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Enter username'
            }
        )
    )

    email = forms.EmailField(
        widget=forms.EmailInput(
            attrs={
                'placeholder': 'Enter email'
            }
        )
    )

    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Enter password'
            }
        )
    )

    confirm_password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'placeholder': 'Confirm password'
            }
        )
    )

    def clean(self):

        cleaned_data = super().clean()

        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password and confirm_password:

            if password != confirm_password:

                raise forms.ValidationError(
                    'Passwords do not match.'
                )

        return cleaned_data