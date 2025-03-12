CREATE TABLE sold_usernames (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    price VARCHAR(50) NOT NULL,
    sale_date TIMESTAMP NOT NULL
);


ALTER TABLE sold_usernames ADD CONSTRAINT unique_username UNIQUE (username);


ALTER TABLE sold_usernames
ALTER COLUMN price TYPE NUMERIC USING REPLACE(price, ',', '')::NUMERIC;