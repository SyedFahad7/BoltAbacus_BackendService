from django.contrib.auth import authenticate, login
from django.shortcuts import render
from django.shortcuts import HttpResponse
from rest_framework import permissions
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
# from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
# from django.utils.decorators import method_decorator

from Authentication.models import User


# method_decorator(csrf_protect, name='dispatch')


class SignIn(APIView):
    permission_classes = (AllowAny,)

    def post(self, request):
        data = self.request.data
        email = data['email']
        password = data['password']
        user = User.objects.filter(email=email).values()
        print(user.exists())
        if user.exists():
            user = user[0]
            user_password = user['encryptedPassword']
            if password == user_password:
                print(user["id"])
                return Response({"id": user["id"],
                                 "email": user["email"],
                                 "role": user["role"],
                                 "firstName": user["firstName"]
                                 },
                                status=status.HTTP_200_OK
                                )
        else:
            return Response({"message": "Invalid Credentials. Try Again"}, status=status.HTTP_401_UNAUTHORIZED)

# @method_decorator(ensure_csrf_cookie, name='dispatch')
# class GetCSRFToken(APIView):
#     permission_classes = (permissions.AllowAny)
#
#     def get(self, request, format=None):
#         return Response({'success': 'CSRF cookie set'})

# Create your views here.