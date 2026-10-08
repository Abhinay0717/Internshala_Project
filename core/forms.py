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