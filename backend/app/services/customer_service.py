import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer


class CustomerService:
    async def get_or_create_customer(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        source_channel: str,
        phone: str | None = None,
        external_customer_id: str | None = None,
        name: str | None = None,
        email: str | None = None,
    ) -> Customer:
        normalized_phone = phone or None
        normalized_external_id = external_customer_id or None

        if normalized_phone:
            customer = await self._find_by_phone(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                phone=normalized_phone,
            )
            if customer is not None:
                await self._update_missing_customer_fields(
                    session,
                    customer,
                    external_customer_id=normalized_external_id,
                    name=name,
                    email=email,
                )
                return customer

        if normalized_external_id:
            customer = await self._find_by_external_customer_id(
                session,
                tenant_id=tenant_id,
                business_id=business_id,
                source_channel=source_channel,
                external_customer_id=normalized_external_id,
            )
            if customer is not None:
                await self._update_missing_customer_fields(
                    session,
                    customer,
                    phone=normalized_phone,
                    name=name,
                    email=email,
                )
                return customer

        if normalized_phone is None and normalized_external_id is None:
            raise ValueError("phone or external_customer_id is required")

        customer = Customer(
            tenant_id=tenant_id,
            business_id=business_id,
            phone=normalized_phone,
            external_customer_id=normalized_external_id,
            source_channel=source_channel,
            name=name,
            email=email,
        )
        session.add(customer)
        await session.flush()
        return customer

    async def _find_by_phone(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        phone: str,
    ) -> Customer | None:
        result = await session.execute(
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.business_id == business_id,
                Customer.phone == phone,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _update_missing_customer_fields(
        self,
        session: AsyncSession,
        customer: Customer,
        *,
        phone: str | None = None,
        external_customer_id: str | None = None,
        name: str | None = None,
        email: str | None = None,
    ) -> None:
        changed = False
        if phone and not customer.phone:
            customer.phone = phone
            changed = True
        if external_customer_id and not customer.external_customer_id:
            customer.external_customer_id = external_customer_id
            changed = True
        if name and not customer.name:
            customer.name = name
            changed = True
        if email and not customer.email:
            customer.email = email
            changed = True
        if changed:
            await session.flush()

    async def _find_by_external_customer_id(
        self,
        session: AsyncSession,
        *,
        tenant_id: uuid.UUID,
        business_id: uuid.UUID,
        source_channel: str,
        external_customer_id: str,
    ) -> Customer | None:
        result = await session.execute(
            select(Customer)
            .where(
                Customer.tenant_id == tenant_id,
                Customer.business_id == business_id,
                Customer.source_channel == source_channel,
                Customer.external_customer_id == external_customer_id,
            )
            .limit(1)
        )
        return result.scalar_one_or_none()
