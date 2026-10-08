from django.core.management.base import BaseCommand
from subscriptions.models import SubscriptionPlan


class Command(BaseCommand):

    help = "Create default subscription plans"

    def handle(self, *args, **kwargs):

        plans = [
            {
                "name": "free",
                "price": 0,
                "monthly_application_limit": 1,
                "description": "Free plan - 1 internship application per month",
            },
            {
                "name": "bronze",
                "price": 100,
                "monthly_application_limit": 3,
                "description": "Bronze plan - up to 3 internship applications per month",
            },
            {
                "name": "silver",
                "price": 300,
                "monthly_application_limit": 5,
                "description": "Silver plan - up to 5 internship applications per month",
            },
            {
                "name": "gold",
                "price": 1000,
                "monthly_application_limit": None,
                "description": "Gold plan - unlimited internship applications",
            },
        ]

        for plan_data in plans:

            plan, created = SubscriptionPlan.objects.update_or_create(
                name=plan_data["name"],
                defaults={
                    "price": plan_data["price"],
                    "monthly_application_limit": plan_data[
                        "monthly_application_limit"
                    ],
                    "description": plan_data["description"],
                    "is_active": True,
                },
            )

            if created:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Created {plan.get_name_display()} plan"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Updated {plan.get_name_display()} plan"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                "All subscription plans are ready."
            )
        )