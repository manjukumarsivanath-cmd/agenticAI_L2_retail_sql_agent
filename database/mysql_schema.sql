CREATE DATABASE IF NOT EXISTS retail_agent_assignment;
USE retail_agent_assignment;

CREATE TABLE IF NOT EXISTS stores (
    store_id    VARCHAR(20) PRIMARY KEY,
    store_name  VARCHAR(100) NOT NULL,
    region      VARCHAR(50),
    city        VARCHAR(50),
    store_type  VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS products (
    product_id    VARCHAR(20) PRIMARY KEY,
    product_name  VARCHAR(100) NOT NULL,
    category      VARCHAR(50),
    sub_category  VARCHAR(50),
    base_price    DECIMAL(10,2)
);

CREATE TABLE IF NOT EXISTS customers (
    customer_id       VARCHAR(20) PRIMARY KEY,
    customer_segment  VARCHAR(50),
    signup_date       DATE,
    preferred_channel VARCHAR(50),
    city              VARCHAR(50)
);

CREATE TABLE IF NOT EXISTS sales_transactions (
    order_id        VARCHAR(20) PRIMARY KEY,
    order_date      DATE,
    store_id        VARCHAR(20),
    product_id      VARCHAR(20),
    customer_id     VARCHAR(20),
    sales_channel    VARCHAR(20),
    units_sold      INT,
    unit_price      DECIMAL(10,2),
    discount_pct    DECIMAL(5,2),
    payment_status   VARCHAR(20),
    delivery_status  VARCHAR(20),
    FOREIGN KEY (store_id) REFERENCES stores(store_id),
    FOREIGN KEY (product_id) REFERENCES products(product_id),
    FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
);

CREATE TABLE IF NOT EXISTS returns (
    return_id     VARCHAR(20) PRIMARY KEY,
    order_id      VARCHAR(20),
    return_date   DATE,
    return_reason VARCHAR(100),
    FOREIGN KEY (order_id) REFERENCES sales_transactions(order_id)
);