# Schema Reference

Database: `retail_agent_assignment` (MySQL 8.4). Defined in `mysql_schema.sql`,
populated from the CSVs in `data/` via `load_data.py`.

## Tables

### `stores`
| Column | Type | Notes |
|---|---|---|
| `store_id` | `VARCHAR(20)` PK | e.g. `ST-001` |
| `store_name` | `VARCHAR(100)` | |
| `region` | `VARCHAR(50)` | e.g. North, South, East, West, Central |
| `city` | `VARCHAR(50)` | |
| `store_type` | `VARCHAR(50)` | e.g. Supermarket |

15 rows.

### `products`
| Column | Type | Notes |
|---|---|---|
| `product_id` | `VARCHAR(20)` PK | e.g. `P-001` |
| `product_name` | `VARCHAR(100)` | |
| `category` | `VARCHAR(50)` | e.g. Beverages, Groceries, Household, Snacks, Personal Care |
| `sub_category` | `VARCHAR(50)` | |
| `base_price` | `DECIMAL(10,2)` | list price, not necessarily the transacted price |

10 rows.

### `customers`
| Column | Type | Notes |
|---|---|---|
| `customer_id` | `VARCHAR(20)` PK | e.g. `C-0001` |
| `customer_segment` | `VARCHAR(50)` | e.g. Regular |
| `signup_date` | `DATE` | |
| `preferred_channel` | `VARCHAR(50)` | e.g. Mobile App |
| `city` | `VARCHAR(50)` | |

80 rows.

### `sales_transactions`
| Column | Type | Notes |
|---|---|---|
| `order_id` | `VARCHAR(20)` PK | e.g. `O-00001`; one row per order (not one row per line item) |
| `order_date` | `DATE` | |
| `store_id` | `VARCHAR(20)` FK -> `stores.store_id` | |
| `product_id` | `VARCHAR(20)` FK -> `products.product_id` | |
| `customer_id` | `VARCHAR(20)` FK -> `customers.customer_id` | |
| `sales_channel` | `VARCHAR(20)` | e.g. Online, In-store, Mobile App, Partner |
| `units_sold` | `INT` | |
| `unit_price` | `DECIMAL(10,2)` | actual transacted price per unit |
| `discount_pct` | `DECIMAL(5,2)` | stored as a whole percentage (e.g. `15` means 15%, not `0.15`) |
| `payment_status` | `VARCHAR(20)` | e.g. Paid |
| `delivery_status` | `VARCHAR(20)` | e.g. Processing |

360 rows.

**Revenue formula.** There is no `amount`/`sales` column - total sale value for
a row is computed as:

```sql
units_sold * unit_price * (1 - discount_pct / 100)
```

### `returns`
| Column | Type | Notes |
|---|---|---|
| `return_id` | `VARCHAR(20)` PK | e.g. `R-0001` |
| `order_id` | `VARCHAR(20)` FK -> `sales_transactions.order_id` | |
| `return_date` | `DATE` | |
| `return_reason` | `VARCHAR(100)` | e.g. Customer Changed Mind |

46 rows.

## Relationships

```
stores (1) ----< sales_transactions >---- (1) products
                       |
                       | (1)
                       v
                  customers (1)

sales_transactions (1) ----< returns
```

`sales_transactions.order_id` is referenced by `returns.order_id` - one order
may have zero or one matching return in this dataset (verified: summing
returns counts per category across `sales_transactions` joined to `returns`
totals exactly 46, matching the `returns` table's own row count, confirming no
join fan-out/double-counting).
