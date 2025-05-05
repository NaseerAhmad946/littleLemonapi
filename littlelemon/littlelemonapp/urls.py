# littlelemonapp/urls.py
from django.urls import path
from .views import menuitems,add_to_cart,place_order,menu_items_edit,assign_delivery_crew,assign_orders,browse_assigned_orders

urlpatterns = [
    path('menu-items/', menuitems),  # Added trailing slash
    path('cart/menu-item',add_to_cart),
    path('order/menu-item',place_order),
    path('menu-items/edit/',menu_items_edit),
    path('manager/assign-delivery-crew/',assign_delivery_crew),
    path('manager/assign-orders/',assign_orders),
    path('delivery_crew/orders/',browse_assigned_orders),
]