from app.analytics import (
    calculate_average_invoice_value,
    calculate_outstanding_amount,
    calculate_paid_amount,
    calculate_total_invoiced,
    get_business_summary,
    get_invoice_status_counts,
    get_top_customer,
)


def main():
    try:
        print("MerchantMate Business Analytics")
        print("=" * 40)

        total_invoiced = calculate_total_invoiced()
        outstanding = calculate_outstanding_amount()
        paid = calculate_paid_amount()
        average = calculate_average_invoice_value()
        statuses = get_invoice_status_counts()
        top_customer = get_top_customer()

        print(f"Total invoiced: AUD {total_invoiced:.2f}")
        print(f"Outstanding amount: AUD {outstanding:.2f}")
        print(f"Paid amount: AUD {paid:.2f}")
        print(f"Average invoice value: AUD {average:.2f}")

        print()
        print("Invoice status counts:")

        for status, count in statuses.items():
            print(f"  {status}: {count}")

        print()
        print("Top customer:")

        if top_customer["customer"]:
            print(
                f"  {top_customer['customer']} "
                f"- AUD {top_customer['total']:.2f}"
            )
        else:
            print("  No customer data available.")

        print()
        print("Complete summary:")
        print(get_business_summary())

    except Exception as exc:
        print("Failed to calculate business analytics.")
        print(exc)


if __name__ == "__main__":
    main()