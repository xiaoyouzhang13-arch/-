from django.urls import path
from . import views

urlpatterns = [
    # 景点
    path('destinations/', views.DestinationListView.as_view(), name='destination_list'),
    path('destinations/<slug:slug>/', views.DestinationDetailView.as_view(), name='destination_detail'),

    # 旅行计划
    path('trips/', views.TripPlanListView.as_view(), name='trip_list'),
    path('trips/create/', views.create_trip, name='create_trip'),
    path('trips/create-from-ai/', views.create_trip_from_ai, name='create_trip_from_ai'),
    path('trips/templates/', views.public_trip_templates, name='trip_templates'),
    path('trips/template/<slug:slug>/clone/', views.clone_trip, name='clone_trip'),
    path('trips/<slug:slug>/', views.TripPlanDetailView.as_view(), name='trip_detail'),
    path('trips/<slug:slug>/update/', views.update_trip, name='update_trip'),
    path('trips/<slug:slug>/delete/', views.delete_trip, name='delete_trip'),
    path('trips/<slug:slug>/toggle-public/', views.toggle_public, name='toggle_public'),
    path('trips/<slug:slug>/tips/', views.trip_tips_view, name='trip_tips'),
    path('trips/<slug:slug>/map/', views.trip_map_view, name='trip_map'),
    path('trips/<slug:slug>/budget/', views.trip_budget_view, name='trip_budget'),
    path('trips/<slug:slug>/publish-note/', views.publish_travel_note, name='publish_note'),

    # 行程项目管理
    path('trips/<slug:trip_slug>/day/<int:day_id>/add-item/', views.add_day_item, name='add_day_item'),
    path('items/<int:item_id>/delete/', views.delete_day_item, name='delete_day_item'),

    # AI行程生成
    path('generate-itinerary/', views.generate_itinerary_page, name='generate_itinerary_page'),
    path('api/generate-itinerary/', views.generate_itinerary_view, name='generate_itinerary'),

    # 多轮对话规划
    path('chat/', views.chat_plan_page, name='chat_plan_page'),
    path('chat/message/', views.chat_plan_message, name='chat_plan_message'),
    path('chat/finalize/', views.chat_plan_finalize, name='chat_plan_finalize'),

    # 游记
    path('notes/', views.TravelNoteListView.as_view(), name='travel_note_list'),
    path('notes/<slug:slug>/', views.TravelNoteDetailView.as_view(), name='travel_note_detail'),
]
