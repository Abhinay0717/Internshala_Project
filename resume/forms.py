from django import forms
from .models import Resume


class ResumeForm(forms.ModelForm):

    class Meta:
        model = Resume

        fields = [
            'full_name',
            'email',
            'phone',
            'profile_photo',
            'career_objective',
            'education',
            'skills',
            'work_experience',
            'internships',
            'projects',
            'certifications',
            'achievements',
            'languages',
            'social_links',
            'references',
            'template',
            'font',
            'color',
        ]

        widgets = {

            'full_name': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your full name'
                }
            ),

            'email': forms.EmailInput(
                attrs={
                    'placeholder': 'Enter your email'
                }
            ),

            'phone': forms.TextInput(
                attrs={
                    'placeholder': 'Enter your phone number'
                }
            ),

            'career_objective': forms.Textarea(
                attrs={
                    'placeholder': 'Write your career objective',
                    'rows': 4
                }
            ),

            'education': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your education details',
                    'rows': 4
                }
            ),

            'skills': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your skills',
                    'rows': 4
                }
            ),

            'work_experience': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your work experience',
                    'rows': 4
                }
            ),

            'internships': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your internship details',
                    'rows': 4
                }
            ),

            'projects': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your projects',
                    'rows': 4
                }
            ),

            'certifications': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your certifications',
                    'rows': 4
                }
            ),

            'achievements': forms.Textarea(
                attrs={
                    'placeholder': 'Enter your achievements',
                    'rows': 4
                }
            ),

            'languages': forms.Textarea(
                attrs={
                    'placeholder': 'Enter languages you know',
                    'rows': 3
                }
            ),

            'social_links': forms.Textarea(
                attrs={
                    'placeholder': 'LinkedIn, GitHub, Portfolio, etc.',
                    'rows': 3
                }
            ),

            'references': forms.Textarea(
                attrs={
                    'placeholder': 'Enter references',
                    'rows': 3
                }
            ),

            'template': forms.Select(
                choices=[
                    ('template1', 'Classic ATS'),
                    ('template2', 'Modern ATS'),
                    ('template3', 'Professional ATS'),
                ]
            ),

            'font': forms.Select(
                choices=[
                    ('Arial', 'Arial'),
                    ('Calibri', 'Calibri'),
                    ('Times New Roman', 'Times New Roman'),
                    ('Georgia', 'Georgia'),
                ]
            ),

            'color': forms.Select(
                choices=[
                    ('black', 'Black'),
                    ('blue', 'Blue'),
                    ('darkgray', 'Dark Gray'),
                ]
            ),
        }


class OTPForm(forms.Form):

    otp = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Enter 6-digit OTP',
                'maxlength': '6'
            }
        )
    )


class ForgotPasswordForm(forms.Form):

    identifier = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                'placeholder': 'Enter your registered email or mobile number'
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