from django import forms
from .models import Post, Comment, Report


class PostForm(forms.ModelForm):

    class Meta:
        model = Post

        fields = [
            'content',
            'media',
            'media_type',
            'privacy',
        ]

        widgets = {
            'content': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 5,
                    'placeholder': 'What do you want to share?'
                }
            ),

            'media_type': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'privacy': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'media': forms.ClearableFileInput(
                attrs={
                    'class': 'form-control'
                }
            ),
        }


class CommentForm(forms.ModelForm):

    class Meta:
        model = Comment

        fields = [
            'text',
        ]

        widgets = {
            'text': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Write a comment...'
                }
            ),
        }


class ReportForm(forms.ModelForm):

    class Meta:
        model = Report

        fields = [
            'reason',
            'description',
        ]

        widgets = {
            'reason': forms.Select(
                attrs={
                    'class': 'form-control'
                }
            ),

            'description': forms.Textarea(
                attrs={
                    'class': 'form-control',
                    'rows': 4,
                    'placeholder': 'Describe the issue...'
                }
            ),
        }