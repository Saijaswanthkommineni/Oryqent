from django.db import transaction
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken

from apps.accounts.models import User


@transaction.atomic
def change_password(*, user: User, new_password: str) -> None:
    """Change credentials and invalidate every token issued under the old version."""

    user.set_password(new_password)
    user.auth_version += 1
    user.save(update_fields=["password", "auth_version"])

    outstanding_token_ids = list(
        OutstandingToken.objects.filter(user=user).values_list("id", flat=True)
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token_id=token_id) for token_id in outstanding_token_ids],
        ignore_conflicts=True,
    )
