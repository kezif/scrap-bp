# scrap-bp
Web scrapping script that would exctract all item names, first page listing prices. And do some filtration and processing

Example of item listing page

![Example of item listing page](https://i.imgur.com/m9GBBte.png)

Json output for item:
```json
    {
        "Item_name": "The Bearded Bombardier",
        "bp_price_ref": 7.06,
        "bp_price_key": 0.16045454545454543,
        "listing_prices": "4.00 ref, 6.77 ref, 6.77 ref, 6.88 ref, 6.88 ref",
        "link": "https://backpack.tf/stats/Unique/Bearded%20Bombardier/Tradable/Craftable",
        "delta": "-3.06 ref, -0.29 ref, -0.29 ref, -0.18 ref, -0.18 ref",
        "perc": "0.57, 0.96, 0.96, 0.97, 0.97",
        "delta_min": -3.0599999999999996
    },
```
