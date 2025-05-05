from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated,AllowAny
from rest_framework.response import Response
from .models import MenuItem, Category,Cart,Order,OrderItem
from .serializers import MenuItemSerializer,OrderSerializer
from django.db import transaction
from django.utils import timezone
from django.contrib.auth.models import User, Group

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def menuitems(request):
    items = MenuItem.objects.all()
    category_name = request.query_params.get('category')
    Price = request.query_params.get('price')
    search = request.query_params.get('search')
    if search:
        try:
            items = MenuItem.objects.filter(title__icontains = search)
        except :
            return Response({'message': f"item {search} not found"},status=404)
    if Price is not None:
            try:
                Price = float(Price)
                items = MenuItem.objects.filter(price = Price)
            except ValueError:
                return Response({'message : invalide price'},status=400)
    if category_name:
        try:
            category = Category.objects.get(title=category_name)
            items = items.filter(category=category)  
        except Category.DoesNotExist:
            return Response({"detail": f"Category '{category_name}' not found."}, status=400)
   
   

    serialized_items = MenuItemSerializer(items, many=True)

    if request.user.groups.filter(name='delivery_crew').exists():
        return Response(serialized_items.data, status=200)
    elif not request.user.groups.exists():  # Check if the user is NOT in any group (likely a customer)
        return Response(serialized_items.data, status=200)
    else:
        return Response({"detail": "Access denied"}, status=403)
    


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def add_to_cart(request):
    item_name = request.data.get('item-name')
    quantity = request.data.get('quantity')

    if not item_name or not quantity:
        return Response({'detail': 'Item name and quantity are required.'}, status=400)

    try:
        quantity = int(quantity)
        item = MenuItem.objects.get(title=item_name)
    except ValueError:
        return Response({'detail': 'Quantity must be a number.'}, status=400)
    except MenuItem.DoesNotExist:
        return Response({'detail': 'Menu item not found.'}, status=404)

  
    total_price = quantity * item.price
    if not request.user.groups.exists():
        cart_item2 = Cart.objects.create(
        user=request.user,
        menuitem=item,
        quantity=quantity,
        unit_price=item.price,
        price=total_price
    )
        cart_item2.save()

    return Response({
        'detail': f"{item_name} added to cart.",
        'quantity': quantity,
        'unit_price': str(item.price),
        'total_price': str(total_price)
    }, status=201)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def place_order(request):
    order_items = request.data.get('order_items', [])
    total_price = 0

    if not request.user.groups.exists():  
        if not order_items:
            return Response({'detail': 'No items provided for the order.'}, status=400)

        with transaction.atomic():  
            # Create the order
            new_order = Order.objects.create(
                user=request.user,
                total=0,  # placeholder, update later
                status=False,
                delivery_crew=None,
                date=timezone.now()
            )

            # Process each item
            for entry in order_items:
                title = entry.get('title')
                quantity = int(entry.get('quantity', 1))

                try:
                    menu_item = MenuItem.objects.get(title=title)
                except MenuItem.DoesNotExist:
                    return Response({'detail': f"Menu item '{title}' not found."}, status=404)

                item_total = menu_item.price * quantity
                total_price += item_total

                # Create order item
                OrderItem.objects.create(
                    order=new_order,
                    menuitem=menu_item,
                    quantity=quantity,
                    unit_price=menu_item.price,
                    price=item_total
                )

            # Update order total
            new_order.total = total_price
            new_order.save()

        return Response({
            'detail': 'Order placed successfully.',
            'total_price': str(total_price),
            'order_id': new_order.id
        }, status=201)

    return Response({'detail': 'Only customers can place orders.'}, status=403)


@api_view(['GET', 'POST', 'PUT', 'PATCH', 'DELETE'])
@permission_classes([IsAuthenticated])
def menu_items_edit(request):
    if request.method == 'GET':
        items = MenuItem.objects.all()
        serializer = MenuItemSerializer(items, many=True)
        return Response(serializer.data)

    if not request.user.groups.filter(name='Manager').exists():
        return Response({'detail': 'Only managers can perform this action.'}, status=403)

    # POST: Create a new menu item
    if request.method == 'POST':
        serializer = MenuItemSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message":"data uploaded"}, status=201)
        return Response(serializer.errors, status=400)

   
    if request.method in ['PUT', 'PATCH']:
        item_name= request.data.get('title')  
        try:
            item = MenuItem.objects.get(title = item_name)
        except MenuItem.DoesNotExist:
            return Response({'detail': 'Menu item not found.'}, status=404)

        serializer = MenuItemSerializer(item, data=request.data, partial=(request.method == 'PATCH'))
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    # DELETE: Delete an item (by id in data)
    if request.method == 'DELETE':
        item_title = request.data.get('title')
    if not item_title:
        return Response({'detail': 'Title is required to delete item.'}, status=400)

    items = MenuItem.objects.filter(title=item_title)
    if not items.exists():
        return Response({'detail': 'Menu item not found.'}, status=404)

    count = items.count()
    items.delete()
    return Response({'detail': f'{count} item(s) with title "{item_title}" deleted.'}, status=204)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def assign_delivery_crew(request):
    # Only managers can assign delivery crew
    if not request.user.groups.filter(name='Manager').exists():
        return Response({'detail': 'Only managers can assign roles.'}, status=403)

    username = request.data.get('username')
    if not username:
        return Response({'detail': 'Username is required.'}, status=400)

    # Find user
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return Response({'detail': 'User not found.'}, status=404)

    # Add user to existing "delivery_crew" group
    try:
        delivery_group = Group.objects.get(name='delivery_crew')
    except Group.DoesNotExist:
        return Response({'detail': 'Delivery crew group not found.'}, status=404)

    user.groups.add(delivery_group)

    return Response({'detail': f'User {username} added to delivery_crew.'}, status=200)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_orders(request):
    
    if not request.user.groups.filter(name='Manager').exists():
        return Response({"message": "Only Manager can assign delivery crew to orders"}, status=403)

    
    username = request.data.get('username')
    order_id = request.data.get('order_id')

    if not username or not order_id:
        return Response({"message": "Username and order_id are required"}, status=400)

    
    try:
        delivery_crew = User.objects.get(username=username)  # ✅ Use `username`, not `Username`
    except User.DoesNotExist:
        return Response({"message": "No user found"}, status=404)

    
    try:
        order = Order.objects.get(id=order_id)
    except Order.DoesNotExist:
        return Response({"message": "Order does not exist"}, status=404)

    # Assign the delivery crew
    order.delivery_crew = delivery_crew
    order.save()

    return Response({"message": f"Order {order_id} assigned to {username}."}, status=200)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def browse_assigned_orders(request):
    # Only delivery crew can access
    if not request.user.groups.filter(name='delivery_crew').exists():
        return Response({"message": "Only delivery crew can access this"}, status=403)

    user = request.user
    # Get only orders assigned to this delivery crew member
    orders = Order.objects.filter(delivery_crew=user)
    serializer = OrderSerializer(orders, many=True)

    return Response(serializer.data)
    




