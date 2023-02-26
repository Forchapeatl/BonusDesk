from django.db import models
from django.contrib.auth.models import User
from datetime import date
from mptt.models import (
    MPTTModel,
    TreeForeignKey
)
from pinax.referrals.models import Referral
from phonenumber_field.modelfields import PhoneNumberField
from django.dispatch import receiver
from django.db.models.signals import post_save
from account.signals import user_signed_up
from django.core.urlresolvers import reverse_lazy


# "Payment" Model
class Payment(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name='Payment author',
    )
    date = models.DateField(
        verbose_name='Payment day',
        default=date.today,
        blank=False,
    ) 
    paid = models.BooleanField(
        verbose_name='Payment State',
        default=False,
        blank=False,
    )


    class Meta:
        db_table = 'payment'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'
        ordering = ["date"]

    def __str__(self):
        return '%s (%s - %s)' % (self.user.username, self.date.strftime("%B"), self.date.strftime("%Y"))


# "Profile" model
class Profile(MPTTModel):
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        verbose_name='User',
    )
    referral = models.OneToOneField(
        Referral,
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        verbose_name='Referral',
    )
    parent = TreeForeignKey(
        'self',
        on_delete=models.CASCADE,
        related_name='children',
        blank=True,
        null=True,
        verbose_name='User parent',
    )
    amount = models.FloatField(
        blank=True,
        null=True,
        verbose_name='Accumulated bonuses for previous months',
    )
    birth_date = models.DateField(
        blank=True,
        null=True,
        verbose_name='Date of birth',
    )
    address = models.CharField(
        blank=False,
        max_length=500,
        verbose_name='Address of residence',
    )
    phone_number = PhoneNumberField(
        blank=False,
        verbose_name='Phone number',
    )
    first_name = models.CharField(
        max_length=250,
        blank=False,
        verbose_name='Name',
    )
    last_name = models.CharField(
        max_length=250,
        blank=False,
        verbose_name='Family name',
    )
    middle_name = models.CharField(
        max_length=250,
        blank=False,
        verbose_name='Surname',
    )

    class Meta:
        db_table = 'profile'
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'

    class MPTTMeta:
        order_insertion_by = ['user']

    def __str__(self):
        return '%s (%s)' % (self.user.username, self.user.email)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


@receiver(user_signed_up)
def handle_user_signed_up(sender, user, form, **kwargs):
    profile = user.profile
    referral = Referral.create(user=user, redirect_to=reverse_lazy('account_signup'))
    profile.referral = referral
    profile.save()
