import asyncio
import json
import config
import logging
from api import Api
from aiohttp import web

app = web.Application()

api = Api(
    config.SHOP_ID,
    config.SENDER_ID,
    config.ORDERADMIN_PUBLIC_KEY,
    config.ORDERADMIN_PRIVATE_KEY,
    config.DADATA_API_KEY,
    config.DADATA_SECRET_KEY
)

logging.basicConfig(level=logging.DEBUG)


async def process_task(data, products, payment):
    try:
        await api.create_order(data['name'], data['email'], data['phone'], payment['subtotal'], payment['amount'],
                               payment['orderid'], data['address'], data['pvz'], products, data['warehouse_id'])
    except Exception as e:
        logging.error(f'Something went wrong: {e}')


async def new_order(request: web.Request):
    data = await request.post()

    if 'test' in data and data['test'] == 'test':
        return web.Response(text="ok")
    if data['formid'] != config.FORM_ID:
        return web.Response(text='wrong form id', status=400)

    products = json.loads(data['products'])
    payment = json.loads(data['payment'])

    asyncio.create_task(process_task(data, products, payment))

    return web.Response(text="ok")


async def on_shutdown(app):
    await api.client.close()


app.add_routes([web.post('/', new_order)])
app.on_shutdown.append(on_shutdown)

if __name__ == '__main__':
    web.run_app(app, port=12345)
