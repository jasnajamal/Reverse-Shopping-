from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password, check_password
from .models import Users, Requirements, Categories, Products, Offers, Orders, RequirementImages, ProductImages, Notifications
from django.utils import timezone


def home(request):
    return render(request, 'marketplace/home.html')


def login_view(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')

        try:
            user = Users.objects.get(email=email)

            password_valid = check_password(password, user.password)

            # Support old accounts created before password hashing
            if not password_valid and user.password == password:
                user.password = make_password(password)
                user.save(update_fields=['password'])
                password_valid = True

            if password_valid:
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
        category_id = request.POST.get('category_id')

        if Users.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': Categories.objects.all()}
            )

        if role not in ['buyer', 'seller']:
            messages.error(request, 'Please select a valid role.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': Categories.objects.all()}
            )

        if role == 'seller' and not category_id:
            messages.error(request, 'Please select a selling category.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': Categories.objects.all()}
            )

        if role == 'buyer':
            category_id = None

        Users.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            role=role,
            category_id=category_id
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
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    buyer = Users.objects.get(id=buyer_id, role='buyer')

    return render(
        request,
        'marketplace/buyer_dashboard.html',
        {'buyer': buyer}
    )

def post_requirement(request):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
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
        image = request.FILES.get('image')

        requirement = Requirements.objects.create(
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

        if image:
            image_path = default_storage.save(
                f'requirement_images/{image.name}',
                image
            )

            RequirementImages.objects.create(
                requirement=requirement,
                image_path=image_path
            )

        # Notify matching sellers about the new requirement
        sellers = Users.objects.filter(
            role='seller',
            category_id=category_id
        )

        for seller in sellers:
            Notifications.objects.create(
                user_id=seller.id,
                message=(
                    f'New buyer requirement. '
                    f'Buyer: {buyer.name}. '
                    f'Product: {product_type}. '
                    f'Budget: ₹{budget_min or "Not specified"} - '
                    f'₹{budget_max or "Not specified"}.'
                ),
                created_at=timezone.now()
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

    if request.session.get('user_role') != 'buyer':
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

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    return render(
        request,
        'marketplace/seller_dashboard.html',
        {'seller': seller}
    )

def selected_orders(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    orders = Orders.objects.filter(
        offer__product__seller=seller
    ).select_related(
        'buyer',
        'offer',
        'offer__product',
        'offer__requirement'
    ).order_by('-id')

    return render(
        request,
        'marketplace/selected_orders.html',
        {
            'orders': orders,
            'seller': seller
        }
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

        own_offer = Offers.objects.filter(
            requirement=requirement,
            product__seller=seller
        ).first()

        all_offers = Offers.objects.filter(
            requirement=requirement
        ).select_related(
            'product',
            'product__seller'
        ).order_by('offer_price')

        competing_offers = all_offers.exclude(
            product__seller=seller
        )

        own_position = None
        price_difference = None
        price_difference_label = None

        lowest_offer = all_offers.first()
        lowest_competitor = competing_offers.first()

        # Check whether buyer has already selected an offer
        selected_order = Orders.objects.filter(
            offer__requirement=requirement
        ).select_related(
            'offer',
            'offer__product',
            'offer__product__seller'
        ).first()

        selected_offer = None

        if selected_order:
            selected_offer = selected_order.offer

        if own_offer:
            own_position = list(all_offers).index(own_offer) + 1

            if lowest_competitor:
                price_difference = (
                    own_offer.offer_price - lowest_competitor.offer_price
                )

                if price_difference > 0:
                    price_difference_label = (
                        f'₹{price_difference} higher'
                    )
                elif price_difference < 0:
                    price_difference_label = (
                        f'₹{abs(price_difference)} lower'
                    )
                else:
                    price_difference_label = 'Same price'

        requirement_data.append({
            'requirement': requirement,
            'own_offer': own_offer,
            'competing_offers': competing_offers,
            'all_offers': all_offers,
            'lowest_offer': lowest_offer,
            'lowest_competitor': lowest_competitor,
            'own_position': own_position,
            'price_difference': price_difference,
            'price_difference_label': price_difference_label,

            # New selected-offer information
            'selected_order': selected_order,
            'selected_offer': selected_offer,
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

    # Allow seller to submit offers only for their category
    if seller.category_id != requirement.category_id:
        return redirect('/buyer-requirements/')

    # Prevent duplicate offers from the same seller
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

        # Get uploaded product image
        product_image = request.FILES.get('product_image')

        # Create product
        product = Products.objects.create(
            seller=seller,
            category=requirement.category,
            product_name=product_name,
            description=product_description or None,
            price=product_price,
            condition_type=condition_type,
            brand=brand or None
        )

        # Save product image
        if product_image:
            image_path = default_storage.save(
                f'product_images/{product_image.name}',
                product_image
            )

            ProductImages.objects.create(
                product=product,
                image_path=image_path
            )

        # Create offer
        Offers.objects.create(
            requirement=requirement,
            product=product,
            offer_price=offer_price,
            delivery_days=delivery_days or None,
            warranty=warranty or None,
            message=message or None
        )

        Notifications.objects.create(
            user_id=requirement.buyer_id,
            message=(
                f'New offer received for your {requirement.product_type} requirement. '
                f'Seller: {seller.name}. '
                f'Product: {product.product_name}. '
                f'Offer Price: ₹{offer_price}. '
                f'Delivery: {delivery_days or "Not specified"} days.'
            )
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

        Notifications.objects.create(
            user_id=offer.requirement.buyer_id,
            message=(
                f'Offer updated. '
                f'Seller: {seller.name}. '
                f'Product: {product.product_name}. '
                f'New Offer Price: ₹{offer.offer_price}. '
                f'Delivery: {offer.delivery_days or "Not specified"} days.'
            ),
            created_at=timezone.now()
        )

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
    ).select_related(
        'product',
        'product__seller'
    ).order_by('offer_price')

    selected_order = Orders.objects.filter(
        buyer_id=buyer_id,
        offer__requirement=requirement
    ).select_related(
        'offer',
        'offer__product',
        'offer__product__seller'
    ).first()

    return render(
        request,
        'marketplace/view_offers.html',
        {
            'requirement': requirement,
            'offers': offers,
            'selected_order': selected_order
        }
    )

def select_offer(request, offer_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    offer = Offers.objects.get(
        id=offer_id,
        requirement__buyer_id=buyer_id
    )

    if Orders.objects.filter(
        buyer_id=buyer_id,
        offer__requirement=offer.requirement
    ).exists():
        messages.info(
            request,
            'You have already selected an offer for this requirement.'
        )
        return redirect(f'/view-offers/{offer.requirement.id}/')

    Orders.objects.create(
        buyer_id=buyer_id,
        offer=offer,
        order_status='pending',
        order_date=timezone.now()
    )

    Notifications.objects.create(
        user_id=offer.product.seller_id,
        message=(
            f'Your offer for {offer.requirement.product_type} '
            f'has been selected by the buyer.'
        ),
        created_at=timezone.now()
    )

    messages.success(
        request,
        f'Offer from {offer.product.seller.name} selected successfully.'
    )

    return redirect(f'/view-offers/{offer.requirement.id}/')
    
def my_offers(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    seller = Users.objects.get(id=seller_id, role='seller')

    offers = Offers.objects.filter(
        product__seller=seller
    ).select_related(
        'product',
        'requirement',
        'requirement__buyer'
    ).order_by('-id')

    return render(
        request,
        'marketplace/my_offers.html',
        {
            'offers': offers,
            'seller': seller
        }
    )

def logout_view(request):
    request.session.flush()
    return redirect('/login/')

def profile(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/login/')

    user = Users.objects.get(id=user_id)

    if request.method == 'POST':
        user.name = request.POST.get('name')
        user.email = request.POST.get('email')

        if user.role == 'seller':
            category_id = request.POST.get('category_id')
            user.category_id = category_id

        user.save()

        messages.success(request, 'Profile updated successfully.')
        return redirect('/profile/')

    categories = Categories.objects.all()

    return render(
        request,
        'marketplace/profile.html',
        {
            'user': user,
            'categories': categories
        }
    )

def notifications(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/login/')

    user_notifications = Notifications.objects.filter(
        user_id=user_id
    ).order_by('-id')

    Notifications.objects.filter(
        user_id=user_id,
        is_read=False
    ).update(is_read=True)

    return render(
        request,
        'marketplace/notifications.html',
        {'notifications': user_notifications}
    )