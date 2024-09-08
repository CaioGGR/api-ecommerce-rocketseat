from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user


app = Flask(__name__)
app.config['SECRET_KEY'] = "minha_chave_123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'

login_manager = LoginManager()
db = SQLAlchemy(app)
login_manager.init_app(app)
login_manager.login_view = 'login' # informa a rota de login
CORS(app) # para que a API interaja com programas externos

# Modelagem
# User (id, username, password)
class User(db.Model, UserMixin):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), nullable=False, unique=True) # nao pode ser vazio e nao ter outro igual
  password = db.Column(db.String(80), nullable=False) # nao pode ser vazio
  cart = db.relationship('CartItem', backref='user', lazy=True)

# Produto (id, name, price, description)
class Product(db.Model):
  id = db.Column(db.Integer, primary_key=True) # chave identificadora, primaria, nao pode ser igual a nenhum outro
  name = db.Column(db.String(120), nullable=False) # o nome precisa existir, entao o mesmo nao e nullable
  price = db.Column(db.Float, nullable=False) # todo produto precisa ter preco, portanto, tambem nao e nullable
  description = db.Column(db.Text, nullable=True) # tipo text e nao String devido o text nao ter limite de caracteres, e a descricao costuma ser longa, pode ter descricao vazia

class CartItem(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
  product_id = db.Column(db.Integer, db.ForeignKey('product.id'), nullable=False)

# inicio
@app.route('/')
def initial():
  return 'API up'

# Autenticacao
@login_manager.user_loader
def load_user(user_id):
  return User.query.get(int(user_id))

# logout na api
@app.route('/logout', methods=["POST"])
@login_required # para ele deslogar, ele precisa estar logado antes
def logout():
  logout_user()
  return jsonify({"message": "Logout successfully"})

# login na api
@app.route('/login', methods=["POST"])
def login():
  data = request.json # pega os dados existentes
  user = User.query.filter_by(username=data.get("username")).first() # pega o primeiro elemento da lista filtrada no bd

  if user and data.get("password") == user.password: # se o usuario existe e se a senha do usuario bate com a do bd
      login_user(user)
      return jsonify({"message": "Logged in successfully"})
  
  return jsonify({"message": "Unauthorized. Invalid credentials"}), 401

# adicionar produto
@app.route('/api/products/add', methods=["POST"])
@login_required # precisa estar logado para utilizar
def add_product():
  data = request.json # pega os dados existentes
  if 'name' in data and 'price' in data:
    product = Product(name=data["name"], price=data["price"], description=data.get("description", ""))
    db.session.add(product)
    db.session.commit()
    return jsonify({"message": "Product added successfully"})
  return jsonify({"message": "Invalid product data"}), 400

# deleta produto
@app.route('/api/products/delete/<int:product_id>', methods=["DELETE"])
@login_required # precisa estar logado para utilizar
def delete_product(product_id):
  # recuperar o produto da base de dados
  # verificar se o produto existe
  # se existe, apagar do bd
  # se nao existe, retornar 404 not found
  product = Product.query.get(product_id)
  if product: # se existe um produto
    db.session.delete(product)
    db.session.commit()
    return jsonify({"message": "Product deleted successfully"})
  return jsonify({"message": "Product not found"}), 404

# mostra detalhes de um produto
@app.route('/api/products/<int:product_id>', methods=["GET"])
def get_product_details(product_id):
  product = Product.query.get(product_id)
  if product: # se existe um produto
    return jsonify({
      "id": product.id,
      "name": product.name,
      "price": product.price,
      "description": product.description
    })
  return jsonify({"message": "Product not found"}), 404

# atualiza info do produto
@app.route('/api/products/update/<int:product_id>', methods=["PUT"])
@login_required # precisa estar logado para utilizar
def update_product(product_id):
  product = Product.query.get(product_id)
  if not product: # se o produto nao existir no banco de dados, da 404
    return jsonify({"message": "Product not found"}), 404
  
  data = request.json
  if 'name' in data:
    product.name = data['name']
  
  if 'price' in data:
    product.price = data['price']
  
  if 'description' in data:
    product.description = data['description']
    
  db.session.commit() # jogar as informacoes pro banco
  return jsonify({"message": "Product updated successfully"})

# mostra todos os produtos
@app.route('/api/products', methods=['GET'])
def get_products():
  products = Product.query.all() # vira uma lista dos produtos do bd
  product_list = []
  for product in products: # percorre a lista e vai mostrando
    product_data = {
      "id": product.id,
      "name": product.name,
      "price": product.price,
    }
    product_list.append(product_data)

  return jsonify(product_list)

# adiciona produto no carrinho
@app.route('/api/cart/add/<int:product_id>', methods=['POST'])
@login_required # tem que estar logado para ter um carrinho
def add_to_cart(product_id):
  user = User.query.get(int(current_user.id))
  product = Product.query.get(product_id)

  if user and product:
    cart_item = CartItem(user_id=user.id, product_id=product.id)
    db.session.add(cart_item)
    db.session.commit()
    return jsonify({"message": 'Item added to the cart successfully'})
  return jsonify({"message": 'Failed to add item to the cart'}), 400

# remove produto do carrinho
@app.route('/api/cart/remove/<int:product_id>', methods=['DELETE'])
@login_required # tem que estar logado para remover item do carrinho
def remove_from_cart(product_id):
  cart_item = CartItem.query.filter_by(user_id=current_user.id, product_id=product_id). first()
  if cart_item:
    db.session.delete(cart_item)
    db.session.commit()
    return jsonify({"message": 'Item removed from the cart successfully'})
  return jsonify({"message": 'Failed to remove item from the cart'}), 400

# mostra os produtos no carrinho
@app.route('/api/cart', methods=['GET'])
@login_required # precisa estar logado para mostrar o carrinho
def view_cart():
  user = User.query.get(int(current_user.id))
  cart_items = user.cart
  cart_content = []
  for cart_item in cart_items:
    product = Product.query.get(cart_item.product_id)
    cart_content.append( {
    "id": cart_item.id,
    "user_id": cart_item.user_id,
    "product_id": cart_item.product_id,
    "product_name": product.name,
    "product_price": product.price
  })
  return jsonify(cart_content)

# Checkout
@app.route('/api/cart/checkout', methods=['POST'])
@login_required
def checkout():
  user = User.query.get(int(current_user.id))
  cart_items = user.cart
  for cart_item in cart_items:
    db.session.delete(cart_item)
  db.session.commit()
  return jsonify({"message": 'Checkout successful. Cart has been cleared.'})

if __name__ == "__main__":
  app.run(debug=True)

