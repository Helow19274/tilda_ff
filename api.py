import config
from datetime import datetime
from aiohttp import ClientSession, BasicAuth


class Api:
    def __init__(self, shop_id, sender_id, public_key, private_key, dadata_key, dadata_secret):
        self.client = ClientSession(raise_for_status=True)
        self.auth = BasicAuth(public_key, private_key)
        self.base = 'https://cdek.orderadmin.ru/api/'
        self.shop_id = shop_id
        self.sender = sender_id
        self.dadata_key = dadata_key
        self.dadata_secret = dadata_secret

    async def create_order(self, name, email, phone, order_price, total_price, order_id, address, pvz, products, warehouse_id):
        payload = {
            'shop': self.shop_id,
            'extId': order_id,
            'currency': 1,
            'date': str(datetime.now()),
            'paymentState': config.PAID,
            'orderPrice': order_price,
            'totalPrice': total_price,
            'profile': {
                'name': name,
                'email': email,
                'phone': phone
            },
            'address': {
                'country': 28
            },
            'eav': {
                'order-reserve-warehouse': warehouse_id,
                'delivery-services-request': True,
                'delivery-services-request-data': {
                    'weight': sum(float(product['pack_m']) for product in products),
                    'payment': total_price if config.PAID == 'not_paid' else '0',
                    'estimatedCost': order_price,
                    'retailPrice': float(total_price) - float(order_price),
                    'rate': 49 if pvz == 'courier' else 48,
                    'sender': self.sender
                }
            },
            'orderProducts': []
        }

        if pvz == 'courier':
            async with self.client.post('https://cleaner.dadata.ru/api/v1/clean/address', headers={'Authorization': f'Token {self.dadata_key}', 'X-Secret': self.dadata_secret}, json=[address]) as r:
                address_data = (await r.json())[0]

            params = {
                'filter[0][type]': 'eq',
                'filter[0][field]': 'extId',
                'filter[0][value]': address_data['postal_code']
            }
            locality = await self.method('delivery-services/postcodes', params, 'GET')

            payload['address'].update({
                'street': address_data['street'] or address_data['settlement_with_type'],
                'house': address_data['house'],
                'notFormal': address_data['result'],
                'postcode': address_data['postal_code'],
                'locality': locality['_embedded']['postcodes'][0]['_embedded']['locality']['id']
            })
        else:
            params = {
                'filter[0][type]': 'eq',
                'filter[0][field]': 'extId',
                'filter[0][value]': pvz
            }
            pvz_data = await self.method('delivery-services/service-points', params, 'GET')
            payload['address'].update({
                'notFormal': pvz_data['_embedded']['servicePoints'][0]['rawAddress'],
                'postcode': pvz_data['_embedded']['servicePoints'][0]['raw']['postalCode'],
                'locality': pvz_data['_embedded']['servicePoints'][0]['_embedded']['locality']['id']
            })

            payload['eav']['delivery-services-request-data']['servicePoint'] = pvz_data['_embedded']['servicePoints'][0]['id']

        for product in products:
            payload['orderProducts'].append({
                'productOffer': {
                    'extId': product['lid']
                },
                'count': product['quantity']
            })

        return await self.method('products/order', payload)

    async def method(self, method, payload, t='POST'):
        if t == 'POST':
            async with self.client.post(f'{self.base}{method}', json=payload, auth=self.auth) as r:
                return await r.json()
        elif t == 'GET':
            async with self.client.get(f'{self.base}{method}', params=payload, auth=self.auth) as r:
                return await r.json()
