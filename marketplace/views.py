from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import make_password, check_password
from .models import Users, Requirements, Categories, Products, Offers


def home(request):
    return render(request, 'marketplace/home.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = Users.objects.get(email=email)

            if check_password(password, user.password):
                request.session['user_id'] = user.id
                request.session['user_role'] = user.role

                if user.role == 'buyer':
                    return redirect('/buyer/')
                elif user.role == 'seller':
                    return redirect('/seller/')
            messages.error(request, 'Invalid email or password.')

        except Users.DoesNotExist:
            messages.error(request, 'Invalid email or password.')

    return render(request, 'marketplace/login.html')


def register_view(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        password = request.POST.get('password')
        role = request.POST.get('role')

        if Users.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(request, 'marketplace/register.html')

        category_id = request.POST.get('category_id')

        Users.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            role=role,
            category_id=category_id or None
        )

        messages.success(request, 'Registration successful. Please login.')
        return redirect('/login/')

    categories = Categories.objects.all()

    return render(
        request,
        'marketplace/register.html',
        {'categories': categories}
    )


def buyer_dashboard(request):
    return render(request, 'marketplace/buyer_dashboard.html')

def post_requirement(request):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    buyer = Users.objects.get(id=buyer_id, role='buyer')

    if request.method == 'POST':
        product_type = request.POST.get('product_type')
        category_id = request.POST.get('category_id')
        budget_min = request.POST.get('budget_min')
        budget_max = request.POST.get('budget_max')
        preferred_brand = request.POST.get('preferred_brand')
        condition_type = request.POST.get('condition_type')
        additional_requirements = request.POST.get('additional_requirements')
        required_by = request.POST.get('required_by')

        Requirements.objects.create(
            buyer=buyer,
            category_id=category_id,
            product_type=product_type,
            budget_min=budget_min or None,
            budget_max=budget_max or None,
            preferred_brand=preferred_brand or None,
            condition_type=condition_type or None,
            additional_requirements=additional_requirements or None,
            required_by=required_by or None
        )

        messages.success(request, 'Requirement posted successfully.')
        return redirect('/my-requirements/')

    categories = Categories.objects.all()

    return render(
        request,
        'marketplace/post_requirement.html',
        {'categories': categories}
    )

def my_requirements(request):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    requirements = Requirements.objects.filter(
        buyer_id=buyer_id
    ).order_by('-id')

    return render(
        request,
        'marketplace/my_requirements.html',
        {'requirements': requirements}
    )

def seller_dashboard(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    return render(
        request,
        'marketplace/seller_dashboard.html',
        {'seller': seller}
    )

def buyer_requirements(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    requirements = Requirements.objects.filter(
        category_id=seller.category_id
    ).order_by('-id')

    requirement_data = []

    for requirement in requirements:
        offer = Offers.objects.filter(
            requirement=requirement,
            product__seller=seller
        ).first()

        requirement_data.append({
            'requirement': requirement,
            'offer': offer
        })

    return render(
        request,
        'marketplace/buyer_requirements.html',
        {
            'requirement_data': requirement_data,
            'seller': seller
        }
    )

def submit_offer(request, requirement_id):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')
    requirement = Requirements.objects.get(id=requirement_id)

    # Check whether this seller already submitted an offer
    existing_offer = Offers.objects.filter(
        requirement=requirement,
        product__seller=seller
    ).first()

    if existing_offer:
        return redirect(f'/update-offer/{existing_offer.id}/')

    if request.method == 'POST':
        product_name = request.POST.get('product_name')
        product_description = request.POST.get('product_description')
        product_price = request.POST.get('product_price')
        condition_type = request.POST.get('condition_type')
        brand = request.POST.get('brand')

        offer_price = request.POST.get('offer_price')
        delivery_days = request.POST.get('delivery_days')
        warranty = request.POST.get('warranty')
        message = request.POST.get('message')

        product = Products.objects.create(
            seller=seller,
            category=requirement.category,
            product_name=product_name,
            description=product_description or None,
            price=product_price,
            condition_type=condition_type,
            brand=brand or None
        )

        Offers.objects.create(
            requirement=requirement,
            product=product,
            offer_price=offer_price,
            delivery_days=delivery_days or None,
            warranty=warranty or None,
            message=message or None
        )

        messages.success(request, 'Offer submitted successfully.')
        return redirect('/buyer-requirements/')

    return render(
        request,
        'marketplace/submit_offer.html',
        {'requirement': requirement}
    )

def update_offer(request, offer_id):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    offer = Offers.objects.get(
        id=offer_id,
        product__seller=seller
    )

    product = offer.product

    if request.method == 'POST':
        product.product_name = request.POST.get('product_name')
        product.description = request.POST.get('product_description') or None
        product.price = request.POST.get('product_price')
        product.condition_type = request.POST.get('condition_type')
        product.brand = request.POST.get('brand') or None
        product.save()

        offer.offer_price = request.POST.get('offer_price')
        offer.delivery_days = request.POST.get('delivery_days') or None
        offer.warranty = request.POST.get('warranty') or None
        offer.message = request.POST.get('message') or None
        offer.save()

        messages.success(request, 'Offer updated successfully.')
        return redirect('/buyer-requirements/')

    return render(
        request,
        'marketplace/update_offer.html',
        {
            'offer': offer,
            'product': product
        }
    )

def view_offers(request, requirement_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    requirement = Requirements.objects.get(
        id=requirement_id,
        buyer_id=buyer_id
    )

    offers = Offers.objects.filter(
        requirement=requirement
    ).select_related('product', 'product__seller').order_by('offer_price')

    return render(
        request,
        'marketplace/view_offers.html',
        {
            'requirement': requirement,
            'offers': offers
        }
    )

def view_offers(request, requirement_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    requirement = Requirements.objects.get(
        id=requirement_id,
        buyer_id=buyer_id
    )

    offers = Offers.objects.filter(
        requirement=requirement
    ).select_related(
        'product',
        'product__seller'
    ).order_by('offer_price')

    return render(
        request,
        'marketplace/view_offers.html',
        {
            'requirement': requirement,
            'offers': offers
        }
    )