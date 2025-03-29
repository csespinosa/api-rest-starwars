import os
from flask import Flask, request, jsonify, url_for
from flask_migrate import Migrate
from flask_swagger import swagger
from flask_cors import CORS
from utils import APIException, generate_sitemap
from admin import setup_admin
from models import db, User, Planet, Character, FavoritePlanet, FavoriteCharacter

app = Flask(__name__)
app.url_map.strict_slashes = False

db_url = os.getenv("DATABASE_URL")
if db_url is not None:
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url.replace("postgres://", "postgresql://")
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = "sqlite:////tmp/test.db"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

MIGRATE = Migrate(app, db)
db.init_app(app)
CORS(app)
setup_admin(app)

@app.errorhandler(APIException)
def handle_invalid_usage(error):
    return jsonify(error.to_dict()), error.status_code

@app.route('/')
def sitemap():
    return generate_sitemap(app)

def get_current_user():
    return User.query.first()

@app.route('/people', methods=['GET'])
def get_all_people():
    characters = Character.query.all()
    return jsonify([character.serialize() for character in characters]), 200

@app.route('/people/<int:people_id>', methods=['GET'])
def get_person(people_id):
    character = Character.query.get(people_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    return jsonify(character.serialize()), 200

@app.route('/planets', methods=['GET'])
def get_all_planets():
    planets = Planet.query.all()
    return jsonify([planet.serialize() for planet in planets]), 200

@app.route('/planets/<int:planet_id>', methods=['GET'])
def get_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": "Planet not found"}), 404
    return jsonify(planet.serialize()), 200

@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    return jsonify([user.serialize() for user in users]), 200

@app.route('/users/favorites', methods=['GET'])
def get_user_favorites():
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No users in the database"}), 404
    
    favorite_planets = FavoritePlanet.query.filter_by(user_id=current_user.id).all()
    favorite_characters = FavoriteCharacter.query.filter_by(user_id=current_user.id).all()
    
    planets = [Planet.query.get(fav.planet_id).serialize() for fav in favorite_planets]
    characters = [Character.query.get(fav.character_id).serialize() for fav in favorite_characters]
    
    return jsonify({
        "planets": planets,
        "people": characters
    }), 200

@app.route('/favorite/planet/<int:planet_id>', methods=['POST'])
def add_favorite_planet(planet_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No users in the database"}), 404
    
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": "Planet not found"}), 404
    
    existing_favorite = FavoritePlanet.query.filter_by(
        user_id=current_user.id, 
        planet_id=planet_id
    ).first()
    
    if existing_favorite:
        return jsonify({"message": "Planet is already a favorite"}), 400
    
    new_favorite = FavoritePlanet(user_id=current_user.id, planet_id=planet_id)
    db.session.add(new_favorite)
    db.session.commit()
    
    return jsonify({"message": "Planet added to favorites"}), 201

@app.route('/favorite/people/<int:people_id>', methods=['POST'])
def add_favorite_character(people_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No users in the database"}), 404
    
    character = Character.query.get(people_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    
    existing_favorite = FavoriteCharacter.query.filter_by(
        user_id=current_user.id, 
        character_id=people_id
    ).first()
    
    if existing_favorite:
        return jsonify({"message": "Character is already a favorite"}), 400
    
    new_favorite = FavoriteCharacter(user_id=current_user.id, character_id=people_id)
    db.session.add(new_favorite)
    db.session.commit()
    
    return jsonify({"message": "Character added to favorites"}), 201

@app.route('/favorite/planet/<int:planet_id>', methods=['DELETE'])
def delete_favorite_planet(planet_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No users in the database"}), 404
    
    favorite = FavoritePlanet.query.filter_by(
        user_id=current_user.id, 
        planet_id=planet_id
    ).first()
    
    if not favorite:
        return jsonify({"error": "Planet is not in favorites"}), 404
    
    db.session.delete(favorite)
    db.session.commit()
    
    return jsonify({"message": "Planet removed from favorites"}), 200

@app.route('/favorite/people/<int:people_id>', methods=['DELETE'])
def delete_favorite_character(people_id):
    current_user = get_current_user()
    if not current_user:
        return jsonify({"error": "No users in the database"}), 404
    
    favorite = FavoriteCharacter.query.filter_by(
        user_id=current_user.id, 
        character_id=people_id
    ).first()
    
    if not favorite:
        return jsonify({"error": "Character is not in favorites"}), 404
    
    db.session.delete(favorite)
    db.session.commit()
    
    return jsonify({"message": "Character removed from favorites"}), 200

@app.route('/planets', methods=['POST'])
def create_planet():
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ['name']
    for field in required_fields:
        if field not in request_data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    new_planet = Planet(
        name=request_data['name'],
        climate=request_data.get('climate'),
        population=request_data.get('population'),
        terrain=request_data.get('terrain')
    )
    
    db.session.add(new_planet)
    db.session.commit()
    
    return jsonify(new_planet.serialize()), 201

@app.route('/planets/<int:planet_id>', methods=['PUT'])
def update_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": "Planet not found"}), 404
    
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' in request_data:
        planet.name = request_data['name']
    if 'climate' in request_data:
        planet.climate = request_data['climate']
    if 'population' in request_data:
        planet.population = request_data['population']
    if 'terrain' in request_data:
        planet.terrain = request_data['terrain']
    
    db.session.commit()
    
    return jsonify(planet.serialize()), 200

@app.route('/planets/<int:planet_id>', methods=['DELETE'])
def delete_planet(planet_id):
    planet = Planet.query.get(planet_id)
    if not planet:
        return jsonify({"error": "Planet not found"}), 404
    
    FavoritePlanet.query.filter_by(planet_id=planet_id).delete()
    
    db.session.delete(planet)
    db.session.commit()
    
    return jsonify({"message": "Planet deleted"}), 200

@app.route('/people', methods=['POST'])
def create_character():
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400
    
    required_fields = ['name']
    for field in required_fields:
        if field not in request_data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    new_character = Character(
        name=request_data['name'],
        height=request_data.get('height'),
        mass=request_data.get('mass'),
        hair_color=request_data.get('hair_color'),
        eye_color=request_data.get('eye_color')
    )
    
    db.session.add(new_character)
    db.session.commit()
    
    return jsonify(new_character.serialize()), 201

@app.route('/people/<int:people_id>', methods=['PUT'])
def update_character(people_id):
    character = Character.query.get(people_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    
    request_data = request.get_json()
    if not request_data:
        return jsonify({"error": "No data provided"}), 400
    
    if 'name' in request_data:
        character.name = request_data['name']
    if 'height' in request_data:
        character.height = request_data['height']
    if 'mass' in request_data:
        character.mass = request_data['mass']
    if 'hair_color' in request_data:
        character.hair_color = request_data['hair_color']
    if 'eye_color' in request_data:
        character.eye_color = request_data['eye_color']
    
    db.session.commit()
    
    return jsonify(character.serialize()), 200

@app.route('/people/<int:people_id>', methods=['DELETE'])
def delete_character(people_id):
    character = Character.query.get(people_id)
    if not character:
        return jsonify({"error": "Character not found"}), 404
    
    FavoriteCharacter.query.filter_by(character_id=people_id).delete()
    
    db.session.delete(character)
    db.session.commit()
    
    return jsonify({"message": "Character deleted"}), 200

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=PORT, debug=False)
