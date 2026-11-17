from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver


MANAGER_GROUP_NAME = "Submission Managers"


@receiver(pre_save, sender=get_user_model())
def track_staff_promotion(sender, instance, using, update_fields, **kwargs):
    instance._grant_manager_role_on_save = False
    if not instance.pk or (update_fields is not None and "is_staff" not in update_fields):
        return
    was_staff = sender.objects.using(using).filter(pk=instance.pk, is_staff=True).exists()
    instance._grant_manager_role_on_save = instance.is_staff and not was_staff


@receiver(post_save, sender=get_user_model())
def grant_new_staff_manager_role(sender, instance, created, using, **kwargs):
    if not instance.is_staff or not (created or instance._grant_manager_role_on_save):
        return
    group = Group.objects.using(using).filter(name=MANAGER_GROUP_NAME).first()
    if group:
        instance.groups.add(group)
