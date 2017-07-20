"""Methods for accessing clients."""
from __future__ import absolute_import

import collections
import json

from api import users


def search(current, query=None):
    if not query:
        raise ValueError("query must be provided.")

    query = query.strip()
    condition = current.db.clients.id > 0

    # Search for a client ID directly.
    if query.startswith("C."):
        condition = current.db.clients.client_id == query
    elif query.startswith("label:"):
        label = query.split(":", 1)[1]
        condition = current.db.clients.labels == label
    else:
        # AppEngine uses Bigtable which does not support `like` operation. We
        # only support a prefix match.
        condition = ((current.db.clients.hostname >= query) &
                     (current.db.clients.hostname < query + u"\ufffd"))

    result = []
    for row in current.db(condition).select(
        orderby_on_limitby=False, limitby=(0, 1000)):
        print row.labels, row.custom_labels
        result.append(dict(
            last=row.last,
            client_id=row.client_id,
            summary=json.loads(row.summary),
            labels=sorted(set(row.labels).union(row.custom_labels))))

    return dict(data=result)

search.args = collections.OrderedDict(
    query="The query string. If it starts with a 'C.' then we display an exact "
    "match. Otherwise we search for a hostname prefix.")


def list_approvers(current):
    """List users which can approve client access."""
    db = current.db
    # TODO: implement conditions.
    approvers = []
    for row in db(db.permissions.role == "Approver").select():
        approvers.append(row.user)

    return dict(data=approvers)


def request_approval(current, client_id, approver, role):
    """Request an approval from the specified user."""

    # Notify the approver that a request is pending.
    users.send_notifications(
        current, approver, "APPROVAL_REQUEST", dict(
            client_id=client_id,
            user=users.get_current_username(current),
            role=role))
    return {}

request_approval.args = collections.OrderedDict(
    client_id="The client to grant access to.",
    approver="The user that should approve the request.",
    role="The role granted.")


def approve_request(current, client_id, user, role):
    """Grant the approval for the client."""
    # Validate the client_id.
    if (client_id.startswith("C.") and len(client_id.split("/")) == 1 and
        role in ["Examiner", "Investigator"]):
        users.add(current, user, "/" + client_id, role)

    return dict()


approve_request.args = collections.OrderedDict(
    client_id="The client to grant access to.",
    user="The user getting the approval.",
    role="The role granted.")



def label(current, client_ids, labels):
    db = current.db
    for row in db(db.clients.client_id.belongs(client_ids)).select():
        row.custom_labels.extend(labels)
        row.update_record(custom_labels=row.custom_labels)

    return {}
