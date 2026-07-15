"""Server-side forms for account, review, newsletter, and address input."""

from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, NewsletterSubscriber, Review


class SignUpForm(UserCreationForm):
    """Registration form that makes a unique email part of the account identity."""
    email = forms.EmailField(required=True)

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("username", "email", "password1", "password2")

    def clean_email(self):
        """Prevent ambiguous email ownership even though usernames remain the login key."""
        email = self.cleaned_data["email"].lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("An account already uses this email address.")
        return email


class LoginForm(AuthenticationForm):
    """Django's secure authentication form with an explicit session-duration choice."""
    remember_me = forms.BooleanField(required=False, initial=False)


class ReviewForm(forms.ModelForm):
    """Validate review content before moderation; approval remains a staff decision."""
    RATING_CHOICES = [(5, "★★★★★ Excellent"), (4, "★★★★☆ Very good"), (3, "★★★☆☆ Good"), (2, "★★☆☆☆ Fair"), (1, "★☆☆☆☆ Poor")]
    rating = forms.TypedChoiceField(choices=RATING_CHOICES, coerce=int, widget=forms.RadioSelect)

    class Meta:
        model = Review
        fields = ("name", "email", "rating", "title", "comment")
        widgets = {"comment": forms.Textarea(attrs={"rows": 5}), "email": forms.EmailInput(attrs={"autocomplete": "email"})}


class NewsletterForm(forms.ModelForm):
    """Minimal consent capture backed by the unique subscriber email constraint."""
    class Meta:
        model = NewsletterSubscriber
        fields = ["email"]


class AddressForm(forms.ModelForm):
    """Restrict editable address fields to customer-owned delivery data."""
    class Meta:
        model = Address
        fields = ("label", "recipient_name", "phone", "line_1", "line_2", "city", "state", "postal_code", "country", "kind", "is_default")
