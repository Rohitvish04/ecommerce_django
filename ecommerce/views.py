from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.db.utils import OperationalError
from .models import Product, Category, OrderItem, Order, UserProfile
from .cart import Cart
from .forms import OrderCreateForm
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

def product_list(request):
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q')
    min_price = request.GET.get('min_price')
    max_price = request.GET.get('max_price')
    brand = request.GET.get('brand')

    try:
        products = Product.objects.all()
    except OperationalError:
        products = Product.objects.none()
    try:
        categories = Category.objects.all()
    except OperationalError:
        categories = []

    if category_slug:
        products = products.filter(category__slug=category_slug)
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) | 
            Q(description__icontains=search_query)
        )
    
    if min_price:
        products = products.filter(price__gte=min_price)
    if max_price:
        products = products.filter(price__lte=max_price)
    
    if brand:
        products = products.filter(brand__icontains=brand)

    return render(request, 'ecommerce/product_list.html', {
        'products': products,
        'categories': categories,
        'current_category': category_slug,
        'cart': Cart(request) # Pass cart to template for badges
    })

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'ecommerce/product_detail.html', {
        'product': product,
        'cart': Cart(request)
    })

# Cart Views
def cart_add(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        update = request.POST.get('update', False)
        cart.add(product=product, quantity=quantity, update_quantity=update)
    else:
        cart.add(product=product)
    return redirect('cart_detail')

def cart_remove(request, product_id):
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect('cart_detail')

def cart_detail(request):
    cart = Cart(request)
    return render(request, 'ecommerce/cart_detail.html', {'cart': cart})

def order_create(request):
    cart = Cart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)
            if request.user.is_authenticated:
                order.user = request.user
            order.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])
            cart.clear()
            return render(request, 'ecommerce/order_created.html', {'order': order})
    else:
        initial_data = {}
        if request.user.is_authenticated:
            initial_data = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email
            }
        form = OrderCreateForm(initial=initial_data)
    return render(request, 'ecommerce/order_create.html', {'cart': cart, 'form': form})

@login_required
def order_history(request):
    orders = Order.objects.filter(user=request.user)
    return render(request, 'ecommerce/order_history.html', {'orders': orders})

@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'ecommerce/order_detail.html', {'order': order})

@login_required
def profile(request):
    user = request.user
    # Ensure a profile exists
    profile = getattr(user, 'userprofile', None)
    if profile is None:
        profile = UserProfile.objects.create(user=user)
    if request.method == 'POST':
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        profile.phone = request.POST.get('phone', profile.phone)
        profile.address = request.POST.get('address', profile.address)
        user.save()
        profile.save()
        return redirect('profile')
    return render(request, 'ecommerce/profile.html', {
        'user_obj': user,
        'profile': profile
    })


