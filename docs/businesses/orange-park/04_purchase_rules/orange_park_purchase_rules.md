# Orange Park Purchase Rules

## Purchase-path state consumption

When `intent=purchase_terms` and `stage=purchase_path`, consume these replies
without resetting to root:

| Customer reply | State |
| --- | --- |
| `повна оплата` | `purchase_path=full_payment` |
| `розтермінування` | `purchase_path=installment` |
| `єОселя` | `purchase_path=e_oselya` |
| `кредит`, `банк`, `фінансування` | `purchase_path=financing` |
| `ваучер` | `purchase_path=voucher` |

For each path:

1. Confirm the selected path.
2. Give a general explanation only.
3. Do not promise exact terms, rates, discounts, deadlines, approvals,
   eligible apartments, first payments, or monthly amounts.
4. Ask whether a manager should prepare or confirm the current calculation.
5. Move to `stage=manager_offer`.
6. If the customer agrees while that stage is active, move to
   `intent=manager_contact`, set `contact_requested=true`, and request the
   native Telegram contact.

## Response guidance

- `full_payment`: explain that current price and any full-payment conditions
  require confirmation.
- `installment`: explain that first payment, term, eligible units, and monthly
  amount are current variables.
- `e_oselya`: explain that program eligibility, buyer requirements, and
  eligible units require confirmation.
- `financing`: explain that bank requirements, approval, rates, and eligible
  units depend on the current program.
- `voucher`: explain that voucher acceptance, documents, valuation, and
  eligible units require confirmation.

After a root purchase-terms question, ask:

`Який варіант вам ближчий: повна оплата, розтермінування чи фінансування?`

Do not request contact merely because the customer selected a purchase path.
Offer the current calculation first. Immediate contact is allowed when the
customer directly requests a manager, exact current terms, or a personal
calculation.
