import json
from datetime import date
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.models import User
from django.http import (
    HttpResponse,
    JsonResponse,
)
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from pinax.referrals.models import Referral
from dashboard.models import (
    Profile,
    Payment,
)
from BonusDesk.settings import (
    PRICE,
    CLASSIC,
    SILVER,
    SILVER_BONUS,
    GOLD,
    GOLD_BONUS,
    PLATINUM,
    PLATINUM_BONUS,
    BRILLIANT,
    BRILLIANT_BONUS,
)
from dashboard.forms import (
    SpecifyParentForm,
    SignupForm,
)
from account.views import SignupView as BaseSignupView


class SignupView(BaseSignupView):
    form_class = SignupForm

    def generate_username(self, form):
        pass

    def after_signup(self, form):
        self.create_profile(form)
        super(SignupView, self).after_signup(form)
        action = Referral.record_response(self.request, "USER_SIGNUP")
        if action is not None:
            referral = Referral.objects.get(id=action.referral.id)
            profile = Profile.objects.get(user=self.created_user)
            profile.parent = Profile.objects.get(user=referral.user)
            profile.save()

    def create_profile(self, form):
        profile = self.created_user.profile
        profile.first_name = form.cleaned_data["first_name"]
        profile.last_name = form.cleaned_data["last_name"]
        profile.middle_name = form.cleaned_data["middle_name"]
        profile.birth_date = form.cleaned_data["birth_date"]
        profile.address = form.cleaned_data["address"]
        profile.phone_number = form.cleaned_data["phone_number"]
        profile.save()


class DashboardView(TemplateView):
    template_name = "dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Current user
        context['user'] = self.request.user

        # The user who brought the current user into the system
        profile = Profile.objects.get(user=self.request.user)
        if profile.parent:
            context['parent'] = profile.parent.user
            parent_amount = (int(PRICE) * 5) / 100
        else:
            context['parent'] = None
            parent_amount = 0

        # Percentage of who invited you
        context['amount_from_parent'] = parent_amount

        # Referrals (Followers)
        referrals = profile.get_descendants().filter(level__lte=profile.level + 4)
        context['referrals'] = referrals

        # Referral code for a specific user.
        if not self.request.user.is_superuser:
            context['referral_code'] = Referral.objects.get(user=self.request.user)

        # Current year and month when the page is accessed            
        current_year = date.today().year
        current_month = date.today().month

        # User account for the current month
        current_month_amount = 0
        
        # Number of users from which receives bonuses in each level
        first_level_bonus_referral_count = 0
        second_level_bonus_referral_count = 0
        third_level_bonus_referral_count = 0
        fourth_level_bonus_referral_count = 0

        # Received amount of money from each level.
        first_level_amount = 0
        second_level_amount = 0
        third_level_amount = 0
        fourth_level_amount = 0

        # Number of followers in each level
        first_level_referral_count = 0
        second_level_referral_count = 0
        third_level_referral_count = 0
        fourth_level_referral_count = 0

        for referral in referrals:
            if Payment.objects.filter(
                    user=referral.user,
                    date__month=current_month,
                    date__year=current_year,
                    paid=True
            ).exists():
                level = referral.level - profile.level
                if level == 1:
                    first_level_bonus_referral_count += 1
                    first_level_referral_count += 1
                    current_month_amount = current_month_amount + (int(PRICE) * 10 / 100)
                    first_level_amount = first_level_amount + (int(PRICE) * 10 / 100)
                elif level == 2:
                    second_level_bonus_referral_count += 1
                    second_level_referral_count += 1
                    current_month_amount = current_month_amount + (int(PRICE) * 5 / 100)
                    second_level_amount = second_level_amount + (int(PRICE) * 5 / 100)
                elif level == 3:
                    third_level_bonus_referral_count += 1
                    third_level_referral_count += 1
                    current_month_amount = current_month_amount + (int(PRICE) * 2.5 / 100)
                    third_level_amount = third_level_amount + (int(PRICE) * 2.5 / 100)
                elif level == 4:
                    fourth_level_bonus_referral_count += 1
                    fourth_level_referral_count += 1
                    current_month_amount = current_month_amount + (int(PRICE) * 1 / 100)
                    fourth_level_amount = fourth_level_amount + (int(PRICE) * 1 / 100)

        context['current_month_amount'] = current_month_amount + parent_amount
        context['first_level_bonus_referral_count'] = first_level_bonus_referral_count
        context['second_level_bonus_referral_count'] = second_level_bonus_referral_count
        context['third_level_bonus_referral_count'] = third_level_bonus_referral_count
        context['fourth_level_bonus_referral_count'] = fourth_level_bonus_referral_count
        context['bonus_referral_count'] = first_level_bonus_referral_count + second_level_bonus_referral_count + third_level_bonus_referral_count + fourth_level_bonus_referral_count
        context['first_level_amount'] = first_level_amount
        context['second_level_amount'] = second_level_amount
        context['third_level_amount'] = third_level_amount
        context['fourth_level_amount'] = fourth_level_amount
        context['first_level_referral_count'] = first_level_referral_count
        context['second_level_referral_count'] = second_level_referral_count
        context['third_level_referral_count'] = third_level_referral_count
        context['fourth_level_referral_count'] = fourth_level_referral_count

        # Accumulations for previous months
        context['last_month_amount'] = profile.amount

        # General savings
        if profile.amount is None:
            amount = current_month_amount + parent_amount
        else:
            amount = current_month_amount + parent_amount + profile.amount
        context['amount'] = amount

        # Number of followers
        context['referrals_count'] = referrals.count()

        # Current user's repayment status for the current month
        payment = Payment.objects.filter(
            user=self.request.user,
            date__month=current_month,
            date__year=current_year,
            paid=True
        ).exists()
        context['payment_status'] = payment

        # Information about how much is left to accumulate before purchasing the package
        global accumulate_status, accumulate_text, accumulate
        if amount <= int(CLASSIC):
            accumulate_status = '"Classic" package'
            accumulate_text = 'Need to accumulate: ' + CLASSIC
            accumulate = "Remaining to accumulate: " + str(int(CLASSIC) - amount)
        elif int(CLASSIC) < amount <= int(SILVER):
            accumulate_status = 'Package "Silver"'
            accumulate_text = 'Необходимо накопить: ' + str(SILVER) + '. Bonus + ' + str(SILVER_BONUS)
            accumulate = int(SILVER) - amount
        elif int(SILVER) < amount <= int(GOLD):
            accumulate_status = 'Package "Gold"'
            accumulate_text = 'Need to accumulate: ' + str(GOLD) + '. Bonus + ' + str(GOLD_BONUS)
            accumulate = int(SILVER) - amount
        elif int(SILVER) < amount <= int(PLATINUM):
            accumulate_status = 'Пакет "Platinum"'
            accumulate_text = 'Need to accumulate: ' + str(PLATINUM) + '. Bonus + ' + str(PLATINUM_BONUS)
            accumulate = int(PLATINUM) - amount
        elif int(PLATINUM) < amount <= int(BRILLIANT):
            accumulate_status = 'Brilliant Package'
            accumulate_text = 'Need to accumulate: ' + str(BRILLIANT) + '. Bonus + ' + str(BRILLIANT_BONUS)
            accumulate = int(BRILLIANT) - amount
        elif amount > int(BRILLIANT):
            accumulate_status = 'Package "Brilliant"'
            accumulate_text = 'You have accumulated the required amount. We give you' + str(BRILLIANT_BONUS)
        context['accumulate_status'] = accumulate_status
        context['accumulate_text'] = accumulate_text
        context['accumulate'] = accumulate

        return context


def username_autocomplete(request):
    if request.is_ajax():
        username = request.GET.get('term', '')
        users = User.objects.filter(username__icontains=username)
        results = []
        for user in users:
            users_json = {
                'id': user.id,
                'label': user.username,
                'value': user.username,
            }
            results.append(users_json)
        data = json.dumps(results)
    else:
        data = 'fail'
    mimetype = 'application/json'
    return HttpResponse(data, mimetype)


def search_user_information(request, username):
    global accumulate_status, accumulate_text, accumulate, amount_from_parent, referral_code

    # Find the user by the entered username
    user = User.objects.get(username__icontains=username)

    # His referral code
    if not user.is_superuser:
        referral_code = Referral.objects.get(user=user)
        
    # Initialize dictionary
    data = dict()

    # The user who brought the current user into the system
    profile = Profile.objects.get(user=user)
    if profile.parent:
        parent = profile.parent.user
        amount_from_parent = (int(PRICE) * 5) / 100
    else:
        parent = None
        amount_from_parent = 0
        
    # Referrals (Followers)
    referrals = profile.get_descendants().filter(level__lte=profile.level + 4)

    # Current year and month when the page is accessed
    current_year = date.today().year
    current_month = date.today().month

    # User account for the current month
    current_month_amount = 0

    # Number of users from which receives bonuses in each level
    first_level_bonus_referral_count = 0
    second_level_bonus_referral_count = 0
    third_level_bonus_referral_count = 0
    fourth_level_bonus_referral_count = 0

    # Received amount of money from each level.
    first_level_amount = 0
    second_level_amount = 0
    third_level_amount = 0
    fourth_level_amount = 0

    # Number of followers in each level
    first_level_referral_count = 0
    second_level_referral_count = 0
    third_level_referral_count = 0
    fourth_level_referral_count = 0

    for referral in referrals:
        if Payment.objects.filter(
                user=referral.user,
                date__month=current_month,
                date__year=current_year,
                paid=True
        ).exists():
            level = referral.level - profile.level
            if level == 1:
                first_level_bonus_referral_count += 1
                first_level_referral_count += 1
                current_month_amount = current_month_amount + (int(PRICE) * 10 / 100)
                first_level_amount = first_level_amount + (int(PRICE) * 10 / 100)
            elif level == 2:
                second_level_bonus_referral_count += 1
                second_level_referral_count += 1
                current_month_amount = current_month_amount + (int(PRICE) * 5 / 100)
                second_level_amount = second_level_amount + (int(PRICE) * 5 / 100)
            elif level == 3:
                third_level_bonus_referral_count += 1
                third_level_referral_count += 1
                current_month_amount = current_month_amount + (int(PRICE) * 2.5 / 100)
                third_level_amount = third_level_amount + (int(PRICE) * 2.5 / 100)
            elif level == 4:
                fourth_level_bonus_referral_count += 1
                fourth_level_referral_count += 1
                current_month_amount = current_month_amount + (int(PRICE) * 1 / 100)
                fourth_level_amount = fourth_level_amount + (int(PRICE) * 1 / 100)

    bonus_referral_count = first_level_bonus_referral_count + second_level_bonus_referral_count + third_level_bonus_referral_count + fourth_level_bonus_referral_count

    # Accumulations for previous months
    last_month_amount = profile.amount

    # General savings
    if profile.amount is None:
        amount = current_month_amount
    else:
        amount = current_month_amount + profile.amount + amount_from_parent
        
    # Number of followers
    referrals_count = referrals.count()

    # Information about how much is left to accumulate before purchasing the package
    if amount <= int(CLASSIC):
        accumulate_status = 'Пакет "Classic"'
        accumulate_text = 'Необходимо накопить: ' + str(CLASSIC)
        accumulate = "Осталось накопить: " + str(int(CLASSIC) - amount)
    elif int(CLASSIC) < amount <= int(SILVER):
        accumulate_status = 'Пакет "Silver"'
        accumulate_text = 'Необходимо накопить: ' + str(SILVER) + '. Бонус + ' + str(SILVER_BONUS)
        accumulate = int(SILVER) - amount
    elif int(SILVER) < amount <= int(GOLD):
        accumulate_status = 'Пакет "Gold"'
        accumulate_text = 'Необходимо накопить: ' + str(GOLD) + '. Бонус + ' + str(GOLD_BONUS)
        accumulate = int(GOLD) - amount
    elif int(GOLD) < amount <= int(PLATINUM):
        accumulate_status = 'Пакет "Platinum"'
        accumulate_text = 'Необходимо накопить: ' + str(PLATINUM) + '. Бонус + ' + str(PLATINUM_BONUS)
        accumulate = int(PLATINUM) - amount
    elif int(PLATINUM) < amount <= int(BRILLIANT):
        accumulate_status = 'Пакет "Brilliant"'
        accumulate_text = 'Необходимо накопить: ' + str(BRILLIANT) + '. Бонус + ' + str(BRILLIANT_BONUS)
        accumulate = int(BRILLIANT) - amount
    elif amount > int(BRILLIANT):
        accumulate_status = 'Пакет "Brilliant"'
        accumulate_text = 'Вы накопили нужную сумму. Мы дарим вам ' + str(BRILLIANT_BONUS)

    # We form the context data that we will transfer to the template
    context = {
        'user': user,
        'request_user': request.user,
        'parent': parent,
        'referrals': referrals,
        'current_month_amount': current_month_amount,
        'first_level_bonus_referral_count': first_level_bonus_referral_count,
        'second_level_bonus_referral_count': second_level_bonus_referral_count,
        'third_level_bonus_referral_count': third_level_bonus_referral_count,
        'fourth_level_bonus_referral_count': fourth_level_bonus_referral_count,
        'bonus_referral_count': bonus_referral_count,
        'first_level_amount': first_level_amount,
        'second_level_amount': second_level_amount,
        'third_level_amount': third_level_amount,
        'fourth_level_amount': fourth_level_amount,
        'first_level_referral_count': first_level_referral_count,
        'second_level_referral_count': second_level_referral_count,
        'third_level_referral_count': third_level_referral_count,
        'fourth_level_referral_count': fourth_level_referral_count,
        'last_month_amount': last_month_amount,
        'amount': amount,
        'referrals_count': referrals_count,
        'accumulate_status': accumulate_status,
        'accumulate_text': accumulate_text,
        'accumulate': accumulate,
        'amount_from_parent': amount_from_parent,
        'referral_code': referral_code,
    }
    data['dashboard_block_about_user'] = render_to_string('dashboard_block.html', context)
    return JsonResponse(data)


def specify_parent(request):
    
    # Initialize dictionary
    data = dict()

    # If "POST" request
    if request.method == 'POST':

        # Initialize the form
        form = SpecifyParentForm(request.POST)

        # If the form is valid
        if form.is_valid():

            # Passing the key - value to the dictionary to check in JS
            data['form_is_valid'] = True

            # Check if there is a user with the same email
            if User.objects.get(email=form.cleaned_data['email']) is not None:
                user = User.objects.get(email=form.cleaned_data['email'])
            else:
                user = None

            # If the user exists
            if user:
                # Passing the key - value to the dictionary to check in JS
                data['user_exist'] = True

                # Profile of the user who made the request
                profile = Profile.objects.get(user=request.user)
                # The profile of the user that was listed as the parent
                parent_profile = Profile.objects.get(user=user)
                # Set the parent
                profile.parent = parent_profile
                # Save data to profile
                profile.save()
                # Percentage of parent (5%)
                ancestor_percentage = (int(PRICE) * 5) / 100
                # Pass variables to the template
                context = {
                    'user': request.user,
                    'request_user': request.user,
                    'parent': profile.parent.user,
                    'amount_from_parent': ancestor_percentage,
                }
                # Initialize the block with information about the parent
                data['parent_html'] = render_to_string('parent.html', context)

                # Initialize initial variables
                current_month_amount = 0
                current_year = date.today().year
                current_month = date.today().month
                # All referrals (followers) of the current user
                referrals = profile.get_descendants().filter(level__lte=profile.level + 4)
                # Calculation of the accumulated amount for the current month for each level
                for referral in referrals:
                    if Payment.objects.filter(
                            user=referral.user,
                            date__month=current_month,
                            date__year=current_year,
                            paid=True).exists():
                        level = referral.level - profile.level
                        if level == 1:
                            current_month_amount = current_month_amount + (int(PRICE) * 10 / 100)
                        elif level == 2:
                            current_month_amount = current_month_amount + (int(PRICE) * 5 / 100)
                        elif level == 3:
                            current_month_amount = current_month_amount + (int(PRICE) * 2.5 / 100)
                        elif level == 4:
                            current_month_amount = current_month_amount + (int(PRICE) * 1 / 100)

                # If there are no savings for previous months                            
                if not profile.amount:
                    last_amount = 0
                else:
                    last_amount = profile.amount
                # Savings for the current month    
                current_month_amount = current_month_amount + ancestor_percentage
                # General savings
                amount = current_month_amount + last_amount
                # Initialize and pass variables to blocks about savings for the current and previous months
                context = {'amount': amount, }
                data['amount_html'] = render_to_string('amount.html', context)
                context = {'current_month_amount': current_month_amount, }
                data['current_month_amount_html'] = render_to_string('current_month_amount.html', context)

                # Block with information about the package
                global accumulate, accumulate_status, accumulate_text
                if amount <= int(CLASSIC):
                    accumulate_status = 'Пакет "Classic"'
                    accumulate_text = 'Необходимо накопить: ' + CLASSIC
                    accumulate = "Осталось накопить: " + str(int(CLASSIC) - amount)
                elif int(CLASSIC) < amount <= int(SILVER):
                    accumulate_status = 'Пакет "Silver"'
                    accumulate_text = 'Необходимо накопить: ' + str(SILVER) + '. Бонус + ' + str(SILVER_BONUS)
                    accumulate = int(SILVER) - amount
                elif int(SILVER) < amount <= int(GOLD):
                    accumulate_status = 'Пакет "Gold"'
                    accumulate_text = 'Необходимо накопить: ' + str(GOLD) + '. Бонус + ' + str(GOLD_BONUS)
                    accumulate = int(SILVER) - amount
                elif int(SILVER) < amount <= int(PLATINUM):
                    accumulate_status = 'Пакет "Platinum"'
                    accumulate_text = 'Необходимо накопить: ' + str(PLATINUM) + '. Бонус + ' + str(PLATINUM_BONUS)
                    accumulate = int(PLATINUM) - amount
                elif int(PLATINUM) < amount <= int(BRILLIANT):
                    accumulate_status = 'Пакет "Brilliant"'
                    accumulate_text = 'Необходимо накопить: ' + str(BRILLIANT) + '. Бонус + ' + str(BRILLIANT_BONUS)
                    accumulate = int(BRILLIANT) - amount
                elif amount > int(BRILLIANT):
                    accumulate_status = 'Пакет "Brilliant"'
                    accumulate_text = 'Вы накопили нужную сумму. Мы дарим вам ' + str(BRILLIANT_BONUS)
                context = {
                    'accumulate_status': accumulate_status,
                    'accumulate_text': accumulate_text,
                    'accumulate': accumulate
                }
                data['accumulate_html'] = render_to_string('accumulate.html', context)
        else:
            data['form_is_valid'] = False
    else:
        form = SpecifyParentForm()
    # Initialize the form and pass a variable to it        
    context = {'specify_parent_form': form}
    data['html_form'] = render_to_string('specify_parent.html', context, request=request)
    # Return JSON
    return JsonResponse(data)
