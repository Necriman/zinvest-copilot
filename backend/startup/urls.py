from django.urls import path

from . import views
from . import network

urlpatterns = [
    path("network", network.directory),
    path("network/recommendations", network.recommendations),
    path("network/connect/<uuid:user_id>", network.connect),
    path("network/connections/<uuid:connection_id>", network.connection_detail),
    path("network/connections/<uuid:connection_id>/messages", network.messages),
    path("network/posts", network.posts),
    path("network/posts/<uuid:post_id>", network.post_detail),
    path("summary", views.summary, name="startup-summary"),
    path("profile", views.profile, name="startup-profile"),
    path("onboarding", views.onboarding, name="startup-onboarding"),
    path("cashflow", views.cashflow, name="startup-cashflow"),
    path("cashflow/<uuid:entry_id>", views.cashflow_detail, name="startup-cashflow-detail"),
    path("employees", views.employees, name="startup-employees"),
    path("employees/import", views.employees_import, name="startup-employees-import"),
    path("employees/<uuid:employee_id>", views.employee_detail, name="startup-employee-detail"),
    path("employees/<uuid:employee_id>/photo", views.employee_photo, name="startup-employee-photo"),
    path("products", views.products, name="startup-products"),
    path("products/import", views.products_import, name="startup-products-import"),
    path("products/<uuid:product_id>", views.product_detail, name="startup-product-detail"),
    path("products/<uuid:product_id>/image", views.product_image, name="startup-product-image"),
    path("assignments", views.assignments, name="startup-assignments"),
    path("assignments/<uuid:assignment_id>", views.assignment_detail, name="startup-assignment-detail"),
    path("todos", views.todos, name="startup-todos"),
    path("todos/<uuid:todo_id>", views.todo_detail, name="startup-todo-detail"),
    path("roadmap", views.roadmap, name="startup-roadmap"),
    path("roadmap/questions", views.roadmap_questions, name="startup-roadmap-questions"),
    path("roadmap/items/<str:item_id>", views.roadmap_item, name="startup-roadmap-item"),
]
