# -*- coding: utf-8 -*-

import json

from cromlech.jwt.components import TokenException
from dolmen.api_engine.responder import reply
from dolmen.api_engine.validation import allowed, validate, cors_aware
from zope.interface import Interface
from zope.schema import ASCIILine, List

from . import USERS
from .cors import options, allow


def protected(app):
    def jwt_protection(environ, start_response, overhead):
        header = environ.get('HTTP_AUTHORIZATION')
        if header is not None and header.startswith('Bearer '):
            token = header[7:]
            try:
                payload = overhead.service.authenticate(token)
                if payload is not None:
                    overhead.auth = payload
                    return app(environ, start_response, overhead)
            except TokenException:
                pass
        return reply(403)
    return jwt_protection


class IUserAction(Interface):
    username = ASCIILine(
        title="User identifier",
        required=True,
    )


class IUsersListing(Interface):
    departments = List(
        title=u"Department identifiers, for an OR request",
        required=False,
        value_type=ASCIILine(),
    )


@allowed('GET')
@validate(IUserAction, 'GET')
def UserDetails(action_request, overhead):
    user_details = USERS.get(action_request.username)
    if user_details is not None:
        return reply(
            200, text=json.dumps(user_details['payload']),
            content_type="application/json")
    return reply(404, text="User not found.")


@cors_aware(options, allow)
@protected
@allowed('GET')
@validate(Interface, 'GET')
def PersonalDetails(action_request, overhead):
    user_details = USERS.get(overhead.auth['user'])
    if user_details is not None:
        return reply(
            200, text=json.dumps(user_details),
            content_type="application/json")
    return reply(500)  # this should not happen


@allowed('GET')
@validate(IUsersListing, 'GET')
def UsersListing(action_request, overhead):
    listing = []
    for username, details in USERS.items():
        payload = details['payload']
        if not action_request.departments:
            listing.append({username: payload})
        elif set(action_request.departments) & set(payload['departments']):
            listing.append({username: payload})
        if action_request.departments and not listing:
            return reply(404, text="No matching users found.")
        return reply(200, text=json.dumps(listing),
                     content_type="application/json")


module = {
    '/details': UserDetails,
    '/list': UsersListing,
    '/personal': PersonalDetails,
}
