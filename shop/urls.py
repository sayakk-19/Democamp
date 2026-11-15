from django.urls import path
from . import views
from .payments import demo_payment

urlpatterns = [
    path("index/", views.index, name="ShopHome"),
    path("about/", views.about, name="AboutUs"),
    path("contact/", views.contact, name="ContactUs"),
    path("tracker/", views.tracker, name="TrackingStatus"),
    path("search/", views.search, name="Search"),
    # path("search.html/", views.search, name="SearchItem"),
    path("products/<int:myid>", views.productView, name="ProductView"),
    path("checkout/", views.checkout, name="Checkout"),
    path("handlerequest/", views.handlerequest, name="HandleRequest"),
    path("paytm/demo/", demo_payment, name="PaytmDemoPayment"),

]

"""
from django.urls import path
from . import views
from .payments import demo_payment

urlpatterns = [
    path("index/", views.index, name="ShopHome"),
    path("about/", views.about, name="AboutUs"),
    path("contact/", views.contact, name="ContactUs"),
    path("tracker/", views.tracker, name="TrackingStatus"),
    path("search/", views.search, name="Search"),
    # path("search.html/", views.search, name="SearchItem"),
    path("products/<int:myid>", views.productView, name="ProductView"),
    path("checkout/", views.checkout, name="Checkout"),
    path("handlerequest/", views.handlerequest, name="HandleRequest"),
    path("paytm/demo/", demo_payment, name="PaytmDemoPayment"),
    path("payment_mode/", views.handlerequest, name="paymode"),
]

"""