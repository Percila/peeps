from django.conf.urls import patterns, url

import views

urlpatterns = patterns('',
    url(r'^$', views.home),
    url(r'^profile$', views.profile),
    url(r'^search$', views.search),
)
