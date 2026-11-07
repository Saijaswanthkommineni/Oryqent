from django.contrib.auth.forms import UserChangeForm, UserCreationForm

from apps.accounts.models import User


class OryqentUserCreationForm(UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ("email", "full_name", "is_platform_admin")


class OryqentUserChangeForm(UserChangeForm):
    class Meta(UserChangeForm.Meta):
        model = User
        fields = "__all__"
