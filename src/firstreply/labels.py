"""The routing queues a ticket can go to, and how Bitext's 27 intents map onto them.

We route to queues (teams), not to the dataset's own categories. See docs/adr/0002-queue-taxonomy.md.
"""
QUEUES = [
    "delivery",            # where is my order, late / missed / wrong-address delivery, delivery options
    "order_change",        # place, change or cancel an order; change shipping address
    "refund_return",       # refunds, returns, damaged / wrong / faulty / missing items
    "billing_payment",     # payment failing, unknown charges, invoices, discounts and prices
    "account",             # login, locked or hacked account, account details, plans and subscriptions
    "complaint_feedback",  # venting, praise or suggestions with no specific transaction to fix
    "talk_to_human",       # "check my DM", can't reach support, vague "please help"
    "other",               # anything else: tech bugs, network, stock questions, off-topic
]

BITEXT_TO_QUEUE = {
    "track_order": "delivery", "delivery_period": "delivery", "delivery_options": "delivery",
    "cancel_order": "order_change", "change_order": "order_change", "place_order": "order_change",
    "change_shipping_address": "order_change", "set_up_shipping_address": "order_change",
    "get_refund": "refund_return", "track_refund": "refund_return", "check_refund_policy": "refund_return",
    "check_cancellation_fee": "refund_return",
    "payment_issue": "billing_payment", "check_payment_methods": "billing_payment",
    "check_invoice": "billing_payment", "get_invoice": "billing_payment",
    "create_account": "account", "delete_account": "account", "edit_account": "account",
    "recover_password": "account", "registration_problems": "account", "switch_account": "account",
    "complaint": "complaint_feedback", "review": "complaint_feedback",
    "contact_customer_service": "talk_to_human", "contact_human_agent": "talk_to_human",
    # newsletter_subscription is dropped: real tweets about "subscriptions" are about paid plans, not newsletters
}
