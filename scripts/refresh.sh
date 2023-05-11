#!/usr/bin/env bash

rm -rf ./project/sample_data/*

unzip ./sample_data/aisles.csv.zip	-d ./project/sample_data/aisles && rm -rf ./project/sample_data/aisles/__MACOSX
unzip ./sample_data/departments.csv.zip	-d ./project/sample_data/departments && rm -rf ./project/sample_data/departments/__MACOSX
unzip ./sample_data/order_products__prior.csv.zip	-d ./project/sample_data/order_products__prior && rm -rf ./project/sample_data/order_products__prior/__MACOSX
unzip ./sample_data/order_products__train.csv.zip	-d ./project/sample_data/order_products__train && rm -rf ./project/sample_data/order_products__train/__MACOSX
unzip ./sample_data/orders.csv.zip	-d ./project/sample_data/orders  && rm -rf ./project/sample_data/orders/__MACOSX
unzip ./sample_data/products.csv.zip	-d ./project/sample_data/products  && rm -rf ./project/sample_data/products/__MACOSX
unzip ./sample_data/sample_submission.csv.zip	-d ./project/sample_data/sample_submission   && rm -rf ./project/sample_data/sample_submission/__MACOSX


chmod +x ./project/*.sh
chmod +x ./project/scripts/*.sh
