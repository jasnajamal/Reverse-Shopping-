from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.files.storage import default_storage
from django.contrib.auth.hashers import make_password, check_password
from .models import Users, Requirements, Categories, Products, Offers, Orders, RequirementImages, ProductImages, Notifications, Reviews
from django.utils import timezone
from django.contrib.auth import authenticate
from django.db.models import Avg
from django.views.decorators.cache import never_cache
from decimal import Decimal, InvalidOperation
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


def validate_image_file(image):
    allowed_types = [
        'image/jpeg',
        'image/png',
        'image/webp'
    ]

    max_size = 5 * 1024 * 1024  # 5 MB

    if image.content_type not in allowed_types:
        return 'Only JPG, PNG, and WEBP images are allowed.'

    if image.size > max_size:
        return 'Each image must be 5 MB or smaller.'

    return None

def home(request):
    return render(request, 'marketplace/home.html')

@never_cache
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
    categories = Categories.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        role = request.POST.get('role', '').strip()
        category_id = request.POST.get('category_id', '').strip()

        # Required field validation
        if not name:
            messages.error(request, 'Full name is required.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        if not email:
            messages.error(request, 'Email address is required.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        try:
            validate_email(email)
        except ValidationError:
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )
        
        if len(name) > 100:
            messages.error(
                request,
                'Full name must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        if len(email) > 100:
            messages.error(
                request,
                'Email address must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        if not password:
            messages.error(request, 'Password is required.')
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        # Basic password length validation
        if len(password) < 8:
            messages.error(
                request,
                'Password must contain at least 8 characters.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        # Duplicate email validation
        if Users.objects.filter(email__iexact=email).exists():
            messages.error(
                request,
                'Email already registered.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        # Role validation
        if role not in ['buyer', 'seller']:
            messages.error(
                request,
                'Please select a valid role.'
            )
            return render(
                request,
                'marketplace/register.html',
                {'categories': categories}
            )

        # Seller category validation
        if role == 'seller':
            if not category_id:
                messages.error(
                    request,
                    'Please select a selling category.'
                )
                return render(
                    request,
                    'marketplace/register.html',
                    {'categories': categories}
                )

            if not Categories.objects.filter(
                id=category_id
            ).exists():
                messages.error(
                    request,
                    'Please select a valid selling category.'
                )
                return render(
                    request,
                    'marketplace/register.html',
                    {'categories': categories}
                )

        else:
            category_id = None

        Users.objects.create(
            name=name,
            email=email,
            password=make_password(password),
            role=role,
            category_id=category_id
        )

        messages.success(
            request,
            'Registration successful. Please login.'
        )
        return redirect('/login/')

    return render(
        request,
        'marketplace/register.html',
        {'categories': categories}
    )

@never_cache
def buyer_dashboard(request):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        buyer = Users.objects.get(
            id=buyer_id,
            role='buyer'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Buyer account not found. Please log in again.'
        )
        return redirect('/login/')

    unread_count = Notifications.objects.filter(
        user_id=buyer_id,
        is_read=False
    ).count()

    return render(
        request,
        'marketplace/buyer_dashboard.html',
        {
            'buyer': buyer,
            'unread_count': unread_count
        }
    )

@never_cache
def post_requirement(request):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        buyer = Users.objects.get(
            id=buyer_id,
            role='buyer'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Buyer account not found. Please log in again.'
        )
        return redirect('/login/')

    categories = Categories.objects.all()

    if request.method == 'POST':
        product_type = request.POST.get('product_type', '').strip()
        category_id = request.POST.get('category_id', '').strip()
        budget_min_raw = request.POST.get('budget_min', '').strip()
        budget_max_raw = request.POST.get('budget_max', '').strip()
        preferred_brand = request.POST.get('preferred_brand', '').strip()
        condition_type = request.POST.get('condition_type', '').strip()
        additional_requirements = request.POST.get(
            'additional_requirements', ''
        ).strip()
        required_by = request.POST.get('required_by', '').strip()
        images = request.FILES.getlist('image')

        for image in images:
            image_error = validate_image_file(image)

            if image_error:
                messages.error(request, image_error)
                return render(
                    request,
                    'marketplace/post_requirement.html',
                    {
                        'categories': categories,
                        'today': timezone.now().date().isoformat()
                    }
                )


        # Required field validation
        if not product_type:
            messages.error(request, 'Product type is required.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )
        
        if len(product_type) > 100:
            messages.error(
                request,
                'Product type must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {
                    'categories': categories,
                    'today': timezone.now().date().isoformat()
                }
            )

        if len(preferred_brand) > 100:
            messages.error(
                request,
                'Preferred brand must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {
                    'categories': categories,
                    'today': timezone.now().date().isoformat()
                }
            )

        if not category_id:
            messages.error(request, 'Category is required.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if not budget_min_raw or not budget_max_raw:
            messages.error(
                request,
                'Minimum and maximum budget are required.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if not condition_type:
            messages.error(request, 'Preferred condition is required.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if not required_by:
            messages.error(request, 'Required date is required.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        # Validate category
        try:
            category = Categories.objects.get(id=category_id)
        except (Categories.DoesNotExist, ValueError):
            messages.error(request, 'Please select a valid category.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        # Validate budget values
        try:
            budget_min = Decimal(budget_min_raw)
            budget_max = Decimal(budget_max_raw)
        except InvalidOperation:
            messages.error(request, 'Please enter valid budget amounts.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if budget_min <= 0 or budget_max <= 0:
            messages.error(
                request,
                'Budget amounts must be greater than zero.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if budget_min > Decimal('99999999.99') or budget_max > Decimal('99999999.99'):
            messages.error(
                request,
                'Budget amounts must not exceed 99,999,999.99.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if budget_min > budget_max:
            messages.error(
                request,
                'Minimum budget cannot be greater than maximum budget.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        # Validate condition
        if condition_type not in ['new', 'used']:
            messages.error(
                request,
                'Please select a valid product condition.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        # Validate required date
        try:
            required_date = timezone.datetime.strptime(
                required_by,
                '%Y-%m-%d'
            ).date()
        except ValueError:
            messages.error(request, 'Please enter a valid required date.')
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        if required_date < timezone.localdate():
            messages.error(
                request,
                'Required date cannot be in the past.'
            )
            return render(
                request,
                'marketplace/post_requirement.html',
                {'categories': categories}
            )

        # Create requirement only after all validations pass
        requirement = Requirements.objects.create(
            buyer=buyer,
            category=category,
            product_type=product_type,
            budget_min=budget_min,
            budget_max=budget_max,
            preferred_brand=preferred_brand or None,
            condition_type=condition_type,
            additional_requirements=additional_requirements or None,
            required_by=required_date
        )

        # Save reference images
        for image in images:
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
            category_id=category.id
        )

        for seller in sellers:
            Notifications.objects.create(
                user_id=seller.id,
                message=(
                    f'New buyer requirement. '
                    f'Buyer: {buyer.name}. '
                    f'Product: {product_type}. '
                    f'Budget: ₹{budget_min} - ₹{budget_max}.'
                ),
                created_at=timezone.now()
            )

        messages.success(request, 'Requirement posted successfully.')
        return redirect('/my-requirements/')

    return render(
        request,
        'marketplace/post_requirement.html',
        {'categories': categories}
    )

@never_cache
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

@never_cache
def seller_dashboard(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

    unread_count = Notifications.objects.filter(
        user_id=seller_id,
        is_read=False
    ).count()

    seller_reviews = Reviews.objects.filter(
        seller_id=seller_id
    )

    average_rating = seller_reviews.aggregate(
        Avg('rating')
    )['rating__avg']

    total_reviews = seller_reviews.count()

    return render(
        request,
        'marketplace/seller_dashboard.html',
        {
            'seller': seller,
            'unread_count': unread_count,
            'average_rating': average_rating,
            'total_reviews': total_reviews
        }
    )

@never_cache   
def selected_orders(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

    orders = Orders.objects.filter(
        offer__product__seller=seller
    ).select_related(
        'buyer',
        'offer',
        'offer__product',
        'offer__requirement'
    ).prefetch_related(
        'reviews_set'
    ).order_by('-id')

    return render(
        request,
        'marketplace/selected_orders.html',
        {
            'orders': orders,
            'seller': seller
        }
    )


@never_cache
def buyer_requirements(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

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

@never_cache
def submit_offer(request, requirement_id):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

    try:
        requirement = Requirements.objects.get(
            id=requirement_id,
            category_id=seller.category_id,
            status__in=['Open', 'Offer Received']
        )
    except Requirements.DoesNotExist:
        messages.error(
            request,
            'This requirement is closed, selected, or unavailable.'
        )
        return redirect('/buyer-requirements/')

    # Prevent duplicate offers from the same seller
    existing_offer = Offers.objects.filter(
        requirement=requirement,
        product__seller=seller
    ).first()

    if existing_offer:
        return redirect(f'/update-offer/{existing_offer.id}/')

    if request.method == 'POST':
        product_name = request.POST.get('product_name', '').strip()
        product_description = request.POST.get(
            'product_description', ''
        ).strip()
        product_price_raw = request.POST.get(
            'product_price', ''
        ).strip()
        condition_type = request.POST.get(
            'condition_type', ''
        ).strip()
        brand = request.POST.get('brand', '').strip()

        offer_price_raw = request.POST.get(
            'offer_price', ''
        ).strip()
        delivery_days_raw = request.POST.get(
            'delivery_days', ''
        ).strip()
        warranty = request.POST.get('warranty', '').strip()
        message = request.POST.get('message', '').strip()

        product_images = request.FILES.getlist('product_image')

        for image in product_images:
            image_error = validate_image_file(image)

            if image_error:
                messages.error(request, image_error)
                return render(
                    request,
                    'marketplace/submit_offer.html',
                    {'requirement': requirement}
                )

        # Required field validation
        if not product_name:
            messages.error(request, 'Product name is required.')
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not product_description:
            messages.error(
                request,
                'Product description is required.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not product_price_raw:
            messages.error(request, 'Product price is required.')
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not condition_type:
            messages.error(request, 'Product condition is required.')
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not brand:
            messages.error(
                request,
                'Brand is required. Enter "Unbranded" if applicable.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not product_images:
            messages.error(
                request,
                'At least one product image is required.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not offer_price_raw:
            messages.error(request, 'Offer price is required.')
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not delivery_days_raw:
            messages.error(request, 'Delivery days is required.')
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if not warranty:
            messages.error(
                request,
                'Warranty information is required. '
                'Enter "No Warranty" if applicable.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if len(product_name) > 150:
            messages.error(
                request,
                'Product name must not exceed 150 characters.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if len(brand) > 100:
            messages.error(
                request,
                'Brand must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if len(warranty) > 100:
            messages.error(
                request,
                'Warranty information must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        # Validate product and offer prices
        try:
            product_price = Decimal(product_price_raw)
            offer_price = Decimal(offer_price_raw)
        except InvalidOperation:
            messages.error(
                request,
                'Please enter valid product and offer prices.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if (
            not product_price.is_finite()
            or not offer_price.is_finite()
        ):
            messages.error(
                request,
                'Please enter valid product and offer prices.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if product_price <= 0:
            messages.error(
                request,
                'Product price must be greater than zero.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if offer_price <= 0:
            messages.error(
                request,
                'Offer price must be greater than zero.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if product_price > Decimal('99999999.99'):
            messages.error(
                request,
                'Product price must not exceed 99,999,999.99.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if offer_price > Decimal('99999999.99'):
            messages.error(
                request,
                'Offer price must not exceed 99,999,999.99.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        # Validate delivery days
        try:
            delivery_days = int(delivery_days_raw)
        except ValueError:
            messages.error(
                request,
                'Delivery days must be a valid whole number.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if delivery_days < 0:
            messages.error(
                request,
                'Delivery days cannot be negative.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        if delivery_days > 365:
            messages.error(
                request,
                'Delivery days cannot exceed 365 days.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        # Validate condition
        if condition_type not in ['new', 'used']:
            messages.error(
                request,
                'Please select a valid product condition.'
            )
            return render(
                request,
                'marketplace/submit_offer.html',
                {'requirement': requirement}
            )

        # Create product only after all validation passes
        product = Products.objects.create(
            seller=seller,
            category=requirement.category,
            product_name=product_name,
            description=product_description,
            price=product_price,
            condition_type=condition_type,
            brand=brand
        )

        # Save product images
        for product_image in product_images:
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
            delivery_days=delivery_days,
            warranty=warranty,
            message=message or None
        )

        # Update requirement status after receiving an offer
        if requirement.status == 'Open':
            requirement.status = 'Offer Received'
            requirement.save(update_fields=['status'])

        Notifications.objects.create(
            user_id=requirement.buyer_id,
            message=(
                f'New offer received for your '
                f'{requirement.product_type} requirement. '
                f'Seller: {seller.name}. '
                f'Product: {product.product_name}. '
                f'Offer Price: ₹{offer_price}. '
                f'Delivery: {delivery_days} days.'
            )
        )

        messages.success(
            request,
            'Offer submitted successfully.'
        )
        return redirect('/buyer-requirements/')

    return render(
        request,
        'marketplace/submit_offer.html',
        {'requirement': requirement}
    )

@never_cache
def update_offer(request, offer_id):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

    try:
        offer = Offers.objects.get(
            id=offer_id,
            product__seller=seller
        )
    except Offers.DoesNotExist:
        messages.error(request, 'Offer not found or unavailable.')
        return redirect('/buyer-requirements/')

    # Prevent updating offers after requirement is closed or selected
    if offer.requirement.status in ['Closed', 'Selected']:
        messages.error(
            request,
            'This offer can no longer be updated because '
            'the requirement is closed or selected.'
        )
        return redirect('/buyer-requirements/')

    product = offer.product

    if request.method == 'POST':
        product_name = request.POST.get(
            'product_name', ''
        ).strip()

        product_description = request.POST.get(
            'product_description', ''
        ).strip()

        product_price_raw = request.POST.get(
            'product_price', ''
        ).strip()

        condition_type = request.POST.get(
            'condition_type', ''
        ).strip()

        brand = request.POST.get(
            'brand', ''
        ).strip()

        offer_price_raw = request.POST.get(
            'offer_price', ''
        ).strip()

        delivery_days_raw = request.POST.get(
            'delivery_days', ''
        ).strip()

        warranty = request.POST.get(
            'warranty', ''
        ).strip()

        message = request.POST.get(
            'message', ''
        ).strip()

        new_product_images = request.FILES.getlist(
            'product_images'
        )

        for image in new_product_images:
            image_error = validate_image_file(image)

            if image_error:
                messages.error(request, image_error)
                return render(
                    request,
                    'marketplace/update_offer.html',
                    {
                        'offer': offer,
                        'product': product
                    }
                )

        # Required field validation
        if not product_name:
            messages.error(
                request,
                'Product name is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not product_description:
            messages.error(
                request,
                'Product description is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not product_price_raw:
            messages.error(
                request,
                'Product price is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not condition_type:
            messages.error(
                request,
                'Product condition is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not brand:
            messages.error(
                request,
                'Brand is required. '
                'Enter "Unbranded" if applicable.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not offer_price_raw:
            messages.error(
                request,
                'Offer price is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not delivery_days_raw:
            messages.error(
                request,
                'Delivery days is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if not warranty:
            messages.error(
                request,
                'Warranty information is required. '
                'Enter "No Warranty" if applicable.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if len(product_name) > 150:
            messages.error(
                request,
                'Product name must not exceed 150 characters.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if len(brand) > 100:
            messages.error(
                request,
                'Brand must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if len(warranty) > 100:
            messages.error(
                request,
                'Warranty information must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        # Validate prices
        try:
            product_price = Decimal(product_price_raw)
            offer_price = Decimal(offer_price_raw)
        except InvalidOperation:
            messages.error(
                request,
                'Please enter valid product and offer prices.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if (
            not product_price.is_finite()
            or not offer_price.is_finite()
        ):
            messages.error(
                request,
                'Please enter valid product and offer prices.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if product_price <= 0:
            messages.error(
                request,
                'Product price must be greater than zero.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if offer_price <= 0:
            messages.error(
                request,
                'Offer price must be greater than zero.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if product_price > Decimal('99999999.99'):
            messages.error(
                request,
                'Product price must not exceed 99,999,999.99.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if offer_price > Decimal('99999999.99'):
            messages.error(
                request,
                'Offer price must not exceed 99,999,999.99.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        # Validate condition
        if condition_type not in ['new', 'used']:
            messages.error(
                request,
                'Please select a valid product condition.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        # Validate delivery days
        try:
            delivery_days = int(delivery_days_raw)
        except ValueError:
            messages.error(
                request,
                'Delivery days must be a valid whole number.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if delivery_days < 0:
            messages.error(
                request,
                'Delivery days cannot be negative.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        if delivery_days > 365:
            messages.error(
                request,
                'Delivery days cannot exceed 365 days.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        # An updated offer must still have at least one product image
        existing_images = ProductImages.objects.filter(
            product=product
        ).exists()

        if not existing_images and not new_product_images:
            messages.error(
                request,
                'At least one product image is required.'
            )
            return render(
                request,
                'marketplace/update_offer.html',
                {
                    'offer': offer,
                    'product': product
                }
            )

        # Update product only after validation passes
        product.product_name = product_name
        product.description = product_description
        product.price = product_price
        product.condition_type = condition_type
        product.brand = brand
        product.save()

        # Add newly uploaded product images
        for product_image in new_product_images:
            image_path = default_storage.save(
                f'product_images/{product_image.name}',
                product_image
            )

            ProductImages.objects.create(
                product=product,
                image_path=image_path
            )

        # Update offer
        offer.offer_price = offer_price
        offer.delivery_days = delivery_days
        offer.warranty = warranty
        offer.message = message or None
        offer.save()

        # Notify buyer
        Notifications.objects.create(
            user_id=offer.requirement.buyer_id,
            message=(
                f'Offer updated. '
                f'Seller: {seller.name}. '
                f'Product: {product.product_name}. '
                f'New Offer Price: ₹{offer.offer_price}. '
                f'Delivery: {offer.delivery_days} days.'
            ),
            created_at=timezone.now()
        )

        messages.success(
            request,
            'Offer updated successfully.'
        )
        return redirect('/buyer-requirements/')

    return render(
        request,
        'marketplace/update_offer.html',
        {
            'offer': offer,
            'product': product
        }
    )

@never_cache
def view_offers(request, requirement_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        requirement = Requirements.objects.get(
            id=requirement_id,
            buyer_id=buyer_id
        )
    except Requirements.DoesNotExist:
        messages.error(
            request,
            'Requirement not found or unavailable.'
        )
        return redirect('/my-requirements/')

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

    existing_review = None

    if selected_order:
        existing_review = Reviews.objects.filter(
            order=selected_order,
            buyer_id=buyer_id
        ).first()

    for offer in offers:
        seller_reviews = Reviews.objects.filter(
            seller_id=offer.product.seller_id
        )

        offer.seller_average_rating = seller_reviews.aggregate(
            Avg('rating')
        )['rating__avg']

        offer.seller_review_count = seller_reviews.count()

    return render(
        request,
        'marketplace/view_offers.html',
        {
            'requirement': requirement,
            'offers': offers,
            'selected_order': selected_order,
            'existing_review': existing_review
        }
    )

@never_cache
def select_offer(request, offer_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    # Offer selection must only happen through POST
    if request.method != 'POST':
        messages.error(
            request,
            'Invalid offer selection request.'
        )
        return redirect('/my-requirements/')

    try:
        offer = Offers.objects.get(
            id=offer_id,
            requirement__buyer_id=buyer_id
        )
    except Offers.DoesNotExist:
        messages.error(
            request,
            'Offer not found or unavailable.'
        )
        return redirect('/my-requirements/')

    # Prevent offer selection for a closed requirement
    if offer.requirement.status == 'Closed':
        messages.error(
            request,
            'This requirement is closed. You cannot select an offer.'
        )
        return redirect(
            f'/view-offers/{offer.requirement.id}/'
        )

    # Prevent selection if requirement is already selected
    if Orders.objects.filter(
        buyer_id=buyer_id,
        offer__requirement=offer.requirement
    ).exists():
        messages.info(
            request,
            'You have already selected an offer for this requirement.'
        )
        return redirect(
            f'/view-offers/{offer.requirement.id}/'
        )

    Orders.objects.create(
        buyer_id=buyer_id,
        offer=offer,
        order_status='pending',
        order_date=timezone.now()
    )

    # Update requirement status
    offer.requirement.status = 'Selected'
    offer.requirement.save(
        update_fields=['status']
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

    return redirect(
        f'/view-offers/{offer.requirement.id}/'
    )

@never_cache   
def my_offers(request):
    seller_id = request.session.get('user_id')

    if not seller_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'seller':
        return redirect('/login/')

    try:
        seller = Users.objects.get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        request.session.flush()
        messages.error(
            request,
            'Seller account not found. Please log in again.'
        )
        return redirect('/login/')

    offers = Offers.objects.filter(
        product__seller=seller
    ).select_related(
        'product',
        'requirement',
        'requirement__buyer'
    ).order_by('-id')

    for offer in offers:
        selected_order = Orders.objects.filter(
            offer__requirement=offer.requirement
        ).first()

        offer.is_selected = (
            selected_order is not None
            and selected_order.offer_id == offer.id
        )

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

@never_cache
def profile(request):
    user_id = request.session.get('user_id')

    if not user_id:
        return redirect('/login/')

    try:
        user = Users.objects.get(id=user_id)
    except Users.DoesNotExist:
        request.session.flush()
        return redirect('/login/')

    categories = Categories.objects.all()

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip().lower()

        # Name validation
        if not name:
            messages.error(
                request,
                'Name is required.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )

        # Email validation
        if not email:
            messages.error(
                request,
                'Email address is required.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )
        
        try:
            validate_email(email)
        except ValidationError:
            messages.error(
                request,
                'Please enter a valid email address.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )

        if len(name) > 100:
            messages.error(
                request,
                'Full name must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )

        if len(email) > 100:
            messages.error(
                request,
                'Email address must not exceed 100 characters.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )

        # Prevent another user's email from being used
        if Users.objects.filter(
            email__iexact=email
        ).exclude(id=user.id).exists():
            messages.error(
                request,
                'This email address is already registered.'
            )
            return render(
                request,
                'marketplace/profile.html',
                {
                    'user': user,
                    'categories': categories
                }
            )

        # Seller category validation
        if user.role == 'seller':
            category_id = request.POST.get(
                'category_id', ''
            ).strip()

            if not category_id:
                messages.error(
                    request,
                    'Please select a selling category.'
                )
                return render(
                    request,
                    'marketplace/profile.html',
                    {
                        'user': user,
                        'categories': categories
                    }
                )

            if not Categories.objects.filter(
                id=category_id
            ).exists():
                messages.error(
                    request,
                    'Please select a valid selling category.'
                )
                return render(
                    request,
                    'marketplace/profile.html',
                    {
                        'user': user,
                        'categories': categories
                    }
                )

            user.category_id = category_id

        else:
            # Buyers must not have a seller category
            user.category_id = None

        user.name = name
        user.email = email
        user.save()

        messages.success(
            request,
            'Profile updated successfully.'
        )
        return redirect('/profile/')

    return render(
        request,
        'marketplace/profile.html',
        {
            'user': user,
            'categories': categories
        }
    )

@never_cache
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

def close_requirement(request, requirement_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        requirement = Requirements.objects.get(
            id=requirement_id,
            buyer_id=buyer_id
        )
    except Requirements.DoesNotExist:
        messages.error(
            request,
            'Requirement not found or unavailable.'
        )
        return redirect('/my-requirements/')

    if request.method == 'POST':
        if requirement.status not in ['Selected', 'Closed']:
            requirement.status = 'Closed'
            requirement.save(update_fields=['status'])

            messages.success(
                request,
                'Requirement closed successfully.'
            )

        return redirect('/my-requirements/')

    return redirect('/my-requirements/')

def add_review(request, order_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        order = Orders.objects.select_related(
            'offer',
            'offer__product',
            'offer__product__seller'
        ).get(
            id=order_id,
            buyer_id=buyer_id
        )
    except Orders.DoesNotExist:
        messages.error(request, 'Order not found.')
        return redirect('/buyer/')

    # Prevent duplicate review for the same order
    if Reviews.objects.filter(
        order=order,
        buyer_id=buyer_id
    ).exists():
        messages.info(
            request,
            'You have already reviewed this order.'
        )
        return redirect(
            f'/view-offers/{order.offer.requirement_id}/'
        )

    if request.method == 'POST':
        rating = request.POST.get('rating')
        review_text = request.POST.get('review_text')

        # Rating must be between 1 and 5
        try:
            rating = int(rating)
        except (TypeError, ValueError):
            rating = 0

        if rating < 1 or rating > 5:
            messages.error(
                request,
                'Please select a rating between 1 and 5.'
            )
            return redirect(
                f'/view-offers/{order.offer.requirement_id}/'
            )

        Reviews.objects.create(
            order=order,
            buyer_id=buyer_id,
            seller_id=order.offer.product.seller_id,
            rating=rating,
            review_text=review_text or None,
            created_at=timezone.now()
        )

        Notifications.objects.create(
            user_id=order.offer.product.seller_id,
            message=(
                f'{order.buyer.name} gave you a {rating}/5 rating '
                f'for {order.offer.product.product_name}.'
            ),
            created_at=timezone.now()
        )

        messages.success(
            request,
            'Your rating and review have been submitted.'
        )

        return redirect(
            f'/view-offers/{order.offer.requirement_id}/'
        )

    return redirect(
        f'/view-offers/{order.offer.requirement_id}/'
    )

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and user.is_superuser:
            request.session['admin_logged_in'] = True
            request.session['admin_username'] = user.username

            return redirect('/custom-admin/')

        messages.error(
            request,
            'Invalid admin username or password.'
        )

        return redirect('/#admin-login')

    return redirect('/#admin-login')


@never_cache
def custom_admin_dashboard(request):
    # Only logged-in admin can access
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    context = {
        'total_buyers': Users.objects.filter(
            role='buyer'
        ).count(),

        'total_sellers': Users.objects.filter(
            role='seller'
        ).count(),

        'total_requirements': Requirements.objects.count(),

        'total_offers': Offers.objects.count(),

        'total_orders': Orders.objects.count(),

        'total_reviews': Reviews.objects.count(),

        'average_rating': Reviews.objects.aggregate(
            Avg('rating')
        )['rating__avg'],

        'recent_requirements': Requirements.objects.select_related(
            'buyer',
            'category'
        ).order_by('-id')[:5],
    }

    return render(
        request,
        'marketplace/admin_dashboard.html',
        context
    )

@never_cache
def admin_manage_buyers(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    buyers = Users.objects.filter(
        role='buyer'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_buyers.html',
        {
            'buyers': buyers
        }
    )

@never_cache
def admin_manage_sellers(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    sellers = Users.objects.filter(
        role='seller'
    ).select_related(
        'category'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_sellers.html',
        {
            'sellers': sellers
        }
    )

@never_cache
def admin_manage_requirements(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    requirements = Requirements.objects.select_related(
        'buyer',
        'category'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_requirements.html',
        {
            'requirements': requirements
        }
    )

@never_cache
def admin_manage_offers(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    offers = Offers.objects.select_related(
        'requirement',
        'product',
        'product__seller'
    ).prefetch_related(
        'orders_set'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_offers.html',
        {
            'offers': offers
        }
    )

@never_cache
def admin_manage_orders(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    orders = Orders.objects.select_related(
        'buyer',
        'offer',
        'offer__product',
        'offer__product__seller',
        'offer__requirement'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_orders.html',
        {
            'orders': orders
        }
    )

@never_cache
def admin_manage_reviews(request):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    reviews = Reviews.objects.select_related(
        'order',
        'buyer',
        'seller'
    ).order_by('-id')

    return render(
        request,
        'marketplace/admin_manage_reviews.html',
        {
            'reviews': reviews
        }
    )

def admin_delete_review(request, review_id):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    if request.method != 'POST':
        return redirect('/custom-admin/reviews/')

    try:
        review = Reviews.objects.get(id=review_id)

        review.delete()

        messages.success(
            request,
            'Review deleted successfully.'
        )

    except Reviews.DoesNotExist:
        messages.error(
            request,
            'Review not found.'
        )

    return redirect('/custom-admin/reviews/')

def admin_close_requirement(request, requirement_id):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    if request.method != 'POST':
        return redirect('/custom-admin/requirements/')

    try:
        requirement = Requirements.objects.get(
            id=requirement_id
        )

        if requirement.status not in ['Closed', 'Selected']:
            requirement.status = 'Closed'
            requirement.save(
                update_fields=['status']
            )

            messages.success(
                request,
                'Requirement closed successfully.'
            )
        else:
            messages.info(
                request,
                'This requirement cannot be closed.'
            )

    except Requirements.DoesNotExist:
        messages.error(
            request,
            'Requirement not found.'
        )

    return redirect('/custom-admin/requirements/')

def admin_remove_offer(request, offer_id):
    if not request.session.get('admin_logged_in'):
        return redirect('/')

    if request.method != 'POST':
        return redirect('/custom-admin/offers/')

    try:
        offer = Offers.objects.get(id=offer_id)

        # Do not delete an offer that has already been selected
        if Orders.objects.filter(offer=offer).exists():
            messages.error(
                request,
                'Selected offer cannot be removed.'
            )
            return redirect('/custom-admin/offers/')

        offer.delete()

        messages.success(
            request,
            'Offer removed successfully.'
        )

    except Offers.DoesNotExist:
        messages.error(
            request,
            'Offer not found.'
        )

    return redirect('/custom-admin/offers/')

@never_cache
def custom_admin_logout(request):
    request.session.flush()
    return redirect('/')

@never_cache
def seller_public_profile(request, seller_id):
    buyer_id = request.session.get('user_id')

    if not buyer_id:
        return redirect('/login/')

    if request.session.get('user_role') != 'buyer':
        return redirect('/login/')

    try:
        seller = Users.objects.select_related(
            'category'
        ).get(
            id=seller_id,
            role='seller'
        )
    except Users.DoesNotExist:
        messages.error(
            request,
            'Seller not found or unavailable.'
        )
        return redirect('/my-requirements/')

    reviews = Reviews.objects.filter(
        seller_id=seller_id
    ).select_related(
        'buyer'
    ).order_by('-id')

    average_rating = reviews.aggregate(
        Avg('rating')
    )['rating__avg']

    total_reviews = reviews.count()

    return render(
        request,
        'marketplace/seller_public_profile.html',
        {
            'seller': seller,
            'reviews': reviews,
            'average_rating': average_rating,
            'total_reviews': total_reviews
        }
    )

