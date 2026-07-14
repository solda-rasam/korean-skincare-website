from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'super_secure_and_secret_key_for_surik_glow'

# SQLite Database Setup
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///surik_glow.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Favorites association table (Many-to-Many)
favorites = db.Table('favorites',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('product_id', db.Integer, db.ForeignKey('product.id'), primary_key=True)
)

# Product Database Model
class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    category = db.Column(db.String(50), nullable=False)  # skincare, makeup, haircare, perfume
    brand = db.Column(db.String(100), nullable=False)
    name = db.Column(db.String(150), nullable=False)
    price = db.Column(db.Float, nullable=False)
    img_icon = db.Column(db.String(50), nullable=False, default="fa-sparkles")
    bg_color = db.Column(db.String(55), default="bg-amber-50")
    icon_color = db.Column(db.String(55), default="text-amber-600")
    best_seller = db.Column(db.Boolean, default=False)
    rating = db.Column(db.Integer, default=5)
    ingredients = db.Column(db.Text, nullable=True)
    benefits = db.Column(db.Text, nullable=True)
    ideal_for = db.Column(db.Text, nullable=True)
    # 🟢 ستون تصویر اضافه شد (به صورت پیش‌فرض عکسی در مسیر مشخص شده قرار می‌گیرد)
    image_url = db.Column(db.String(255), nullable=True, default="images/products/default.jpg")

    def to_dict(self, user_id=None):
        is_liked = False
        if user_id:
            user = User.query.get(user_id)
            if user and self in user.liked_products:
                is_liked = True

        return {
            "id": f"db_{self.id}",
            "db_id": self.id,
            "category": self.category,
            "brand": self.brand,
            "name": self.name,
            "price": self.price,
            "imgIcon": self.img_icon,
            "bgColor": self.bg_color,
            "iconColor": self.icon_color,
            "bestSeller": self.best_seller,
            "rating": self.rating,
            "ingredients": self.ingredients or "Natural Korean Ingredients",
            "benefits": self.benefits or "",
            "idealFor": self.ideal_for or "All Skin Types",
            "isLiked": is_liked,
            # 🟢 آدرس تصویر جهت ارسال به فرانت‌اند اضافه شد
            "imageUrl": self.image_url
        }

# User Database Model
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    
    liked_products = db.relationship('Product', secondary=favorites, lazy='subquery',
        backref=db.backref('liked_by', lazy=True))

# API to fetch products with live like status
@app.route('/api/products')
def get_products_api():
    current_user_id = session.get('user_id')
    db_products = Product.query.all()
    products_list = [p.to_dict(user_id=current_user_id) for p in db_products]
    return jsonify(products_list)

# Toggle like status
@app.route('/api/favorite/<int:product_id>', methods=['POST'])
def toggle_favorite(product_id):
    if 'user_id' not in session:
        return jsonify({"success": False, "error": "Please login first"}), 401
    
    user = User.query.get(session['user_id'])
    product = Product.query.get(product_id)
    
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404
        
    if product in user.liked_products:
        user.liked_products.remove(product)
        status = "unliked"
    else:
        user.liked_products.append(product)
        status = "liked"
        
    db.session.commit()
    return jsonify({"success": True, "status": status})

# Home Page Route
@app.route('/')
def home():
    username = session.get('username')
    is_admin = session.get('is_admin', False)
    return render_template('index.html', username=username, is_admin=is_admin)

# Register Route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        if User.query.filter_by(username=username).first():
            flash("This username is already taken.")
            return redirect(url_for('register'))
            
        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password_hash=hashed_password, is_admin=False)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for('login'))
        
    return render_template('register.html')

# Dual-purpose Login Route (Admin & Customers)
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username').strip()
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            flash(f"Welcome back, {username}!")
            if user.is_admin:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('home'))
            
        flash("Invalid username or password.")
    return render_template('login.html')

# Logout Route
@app.route('/logout')
def logout():
    session.clear()
    flash("Logged out successfully.")
    return redirect(url_for('home'))

# Admin Dashboard Route
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    if not session.get('is_admin'):
        flash("Access denied. Admin authorization required.")
        return redirect(url_for('home'))
        
    if request.method == 'POST':
        category = request.form.get('category')
        brand = request.form.get('brand')
        name = request.form.get('name')
        price = float(request.form.get('price'))
        img_icon = request.form.get('img_icon', 'fa-sparkles')
        bg_color = request.form.get('bg_color', 'bg-amber-50')
        icon_color = request.form.get('icon_color', 'text-amber-600')
        best_seller = True if request.form.get('best_seller') else False
        ingredients = request.form.get('ingredients')
        benefits = request.form.get('benefits')
        ideal_for = request.form.get('ideal_for')
        # 🟢 دریافت آدرس عکس از فرم ادمین (در صورتی که در قالب داشبورد فیلد آن را بسازید)
        image_url = request.form.get('image_url', 'images/products/default.jpg')

        new_prod = Product(
            category=category, brand=brand, name=name, price=price,
            img_icon=img_icon, bg_color=bg_color, icon_color=icon_color,
            best_seller=best_seller, ingredients=ingredients,
            benefits=benefits, ideal_for=ideal_for,
            image_url=image_url # 🟢 ذخیره فیلد عکس در دیتابیس
        )
        db.session.add(new_prod)
        db.session.commit()
        flash("Product added successfully!")
        return redirect(url_for('home'))

    return render_template('dashboard.html')

# Initialize DB Route
@app.route('/init-db')
def init_db():
    db.create_all()
    
    # Create Default Admin
    if not User.query.filter_by(username="solda").first():
        hashed_password = generate_password_hash("securepassword123")
        admin = User(username="solda", password_hash=hashed_password, is_admin=True)
        db.session.add(admin)

    # Insert 40 Korean Products
    if Product.query.count() == 0:
        initial_products = [
            # === SKINCARE (10 Products) ===
            Product(
                category="skincare", brand="Beauty of Joseon", name="Relief Sun: Rice + Probiotics SPF50+",
                price=18.00, img_icon="fa-sun", bg_color="bg-amber-50/70", icon_color="text-amber-600",
                best_seller=True, rating=5, ideal_for="All skin types, especially dry or sensitive skin",
                ingredients="Rice Extract 30%, Grain Probiotics Complex, Niacinamide, Adenosine",
                benefits="Lightweight, non-sticky organic sunscreen that nourishes and protects skin with zero white cast.",
                # 🟢 مسیر عکس ضد آفتاب اضافه شد
                image_url="images/sunrice.webp" 
            ),
            Product(
                category="skincare", brand="COSRX", name="Advanced Snail 96 Mucin Power Essence",
                price=21.00, img_icon="fa-droplet", bg_color="bg-stone-100", icon_color="text-stone-600",
                best_seller=True, rating=5, ideal_for="Dehydrated, acne-prone, or dull skin",
                ingredients="Snail Secretion Filtrate 96.3%, Sodium Hyaluronate, Allantoin, Panthenol",
                benefits="Intense hydration, heals compromised skin barriers, and fades acne scars while leaving a natural glow.",
                image_url="images/snail.jpg" 
            ),
            Product(
                category="skincare", brand="Laneige", name="Lip Sleeping Mask (Berry)",
                price=24.00, img_icon="fa-jar", bg_color="bg-pink-50/70", icon_color="text-pink-500",
                best_seller=True, rating=5, ideal_for="Dry, chapped, or flaky lips",
                ingredients="Shea Butter, Beta-glucan, Cranberry/Strawberry Extracts, Vitamin C",
                benefits="Softens dead skin cells overnight, providing plump, deeply hydrated lips by the morning.",
                 image_url="images/lipmask.jpg" 

            ),
            Product(
                category="skincare", brand="I'm From", name="Rice Toner",
                price=28.00, img_icon="fa-water", bg_color="bg-amber-50/50", icon_color="text-amber-500",
                best_seller=False, rating=4, ideal_for="Dull, fatigued, or aging skin",
                ingredients="77.78% Rice Extract, Amaranthus Caudatus Seed Extract, Portulaca Oleracea Extract",
                benefits="Formulated with organic Yeoju rice to eliminate impurities and hydrate deep within the skin barrier.",
                image_url="images/ricetoner.webp"
            ),
            Product(
                category="skincare", brand="Anua", name="Heartleaf 77% Soothing Toner",
                price=23.00, img_icon="fa-heart", bg_color="bg-emerald-50/60", icon_color="text-emerald-600",
                best_seller=True, rating=5, ideal_for="Acne-prone and highly sensitive skin",
                ingredients="77% Houttuynia Cordata (Heartleaf) Extract, Centella Asiatica, Chamomile",
                benefits="Extremely soothing toner that controls sebum production, reduces redness, and calms acne-prone skin.",
                image_url="images/77.webp"

            ),
            Product(
                category="skincare", brand="SKIN1004", name="Madagascar Centella Ampoule",
                price=22.00, img_icon="fa-leaf", bg_color="bg-emerald-50/40", icon_color="text-emerald-500",
                best_seller=False, rating=5, ideal_for="Sensitive, irritated, and red skin",
                ingredients="100% Centella Asiatica Extract from Madagascar",
                benefits="An all-in-one ampoule to replenish, soothe, and rejuvenate skin while strengthening the outer barrier.",
                image_url="images/centella.png"
            ),
            Product(
                category="skincare", brand="Some By Mi", name="AHA BHA PHA 30Days Miracle Toner",
                price=19.00, img_icon="fa-spray-can-sparkles", bg_color="bg-emerald-50/70", icon_color="text-teal-600",
                best_seller=False, rating=4, ideal_for="Oily, acne-prone skin with large pores",
                ingredients="Real Teatree 10,000ppm, AHA, BHA, PHA, Niacinamide",
                benefits="Gently exfoliates dead skin cells, clears clogged pores, and relieves inflammation within 30 days.",
                 image_url="images/toner.jpg"
            ),
            Product(
                category="skincare", brand="Round Lab", name="Birch Juice Moisturizing Cream",
                price=25.00, img_icon="fa-snowflake", bg_color="bg-sky-50/70", icon_color="text-sky-500",
                best_seller=True, rating=5, ideal_for="Dry, dehydrated, or combination skin",
                ingredients="Birch Sap, Vita Hyaluronic Acid, Jojoba Esters",
                benefits="Locks in high-potency moisture for 48 hours without feeling heavy, leaving a refreshing finish.",
                 image_url="images/cream.jpg"
            ),
            Product(
                category="skincare", brand="Haruharu WONDER", name="Black Rice Hyaluronic Toner",
                price=20.00, img_icon="fa-cloud-rain", bg_color="bg-indigo-50/50", icon_color="text-indigo-600",
                best_seller=False, rating=4, ideal_for="Anti-aging, dry skin seeking deep elasticity",
                ingredients="Fermented Black Rice Extract, Bamboo Shoot Bark Extract, Hyaluronic Acid",
                benefits="Boosts skin elasticity, protects against free radicals, and delivers immediate moisture tension.",
                 image_url="images/blackrice.jpg"
            ),
            Product(
                category="skincare", brand="Dear, Klairs", name="Freshly Juiced Vitamin Drop",
                price=23.00, img_icon="fa-flask", bg_color="bg-stone-50", icon_color="text-yellow-600",
                best_seller=False, rating=5, ideal_for="Hyperpigmentation and dull skin tones",
                ingredients="Pure Vitamin C (5% L-Ascorbic Acid), Centella Asiatica, Yuzu Extract",
                benefits="An effective daily serum designed with safe, non-irritating Vitamin C to brighten and clear dark spots.",
                 image_url="images/vitamin.jpg"
            ),

            # === MAKEUP (10 Products) ===
            Product(
                category="makeup", brand="Rom&nd", name="Juicy Lasting Tint (Bare Grape)",
                price=14.00, img_icon="fa-wand-magic-sparkles", bg_color="bg-rose-50/70", icon_color="text-rose-500",
                best_seller=True, rating=5, ideal_for="Cool-toned daily juicy lip looks",
                ingredients="Water, Octyldodecanol, Glycerin, Fruit Extracts",
                benefits="Creates gorgeous, glass-like glossy lips with a beautiful fruity tint that lasts for hours.",
                 image_url="images/1.png"
            ),
            Product(
                category="makeup", brand="Missha", name="M Perfect Cover BB Cream SPF42",
                price=17.00, img_icon="fa-id-card", bg_color="bg-amber-100/50", icon_color="text-amber-800",
                best_seller=True, rating=5, ideal_for="All skin types seeking natural, dewy coverage",
                ingredients="Hyaluronic Acid, Ceramide, Rosemary & Chamomile extracts",
                benefits="Combines skincare and high-coverage makeup, shielding from UV rays while concealing dark spots.",
                image_url="images/2.jpg"
            ),
            Product(
                category="makeup", brand="Clio", name="Kill Cover Mesh Glow Cushion",
                price=32.00, img_icon="fa-circle-notch", bg_color="bg-pink-50/40", icon_color="text-pink-600",
                best_seller=True, rating=5, ideal_for="Glass skin effects and dry skin types",
                ingredients="Chamomilla Recutita Flower Extract, D-Panthenol, Hyaluronic Acid",
                benefits="Delivers ultra-lightweight, seamless coverage with a mesmerizing water-glow finish.",
                 image_url="images/3.jpg"
            ),
            Product(
                category="makeup", brand="Peripera", name="Ink Velvet Lip Tint",
                price=11.00, img_icon="fa-paint-brush", bg_color="bg-red-50/70", icon_color="text-red-500",
                best_seller=False, rating=4, ideal_for="Bold matte velvet gradients",
                ingredients="Dimethicone, Silk Proteins, Vitamin E",
                benefits="The iconic whipped velvet lip tint that coats your lips in intense, weightless, and velvety colors.",
                 image_url="images/4.jpg"
            ),
            Product(
                category="makeup", brand="unleashia", name="Get Loose Glitter Gel",
                price=15.00, img_icon="fa-star", bg_color="bg-purple-50/40", icon_color="text-purple-500",
                best_seller=False, rating=4, ideal_for="Festive eye and face glitter accents",
                ingredients="Eco-friendly Biodegradable Glitters, Water-gel base",
                benefits="A high-adherence, multi-use glitter gel that sparkles intensely under lighting without irritation.",
                 image_url="images/5.jpg"
            ),
            Product(
                category="makeup", brand="Laka", name="Fruity Glam Tint",
                price=16.00, img_icon="fa-wine-bottle", bg_color="bg-rose-50/50", icon_color="text-rose-400",
                best_seller=False, rating=5, ideal_for="Vegan makeup lovers seeking high shine",
                ingredients="100% Vegan botanical oils, rich fruit extracts",
                benefits="Super-moisturizing gloss formula with deep, natural fruit juices that naturally volumize the lips.",
                image_url="images/6.jpg"
            ),
            Product(
                category="makeup", brand="Etude House", name="Dear Darling Water Tint",
                price=8.00, img_icon="fa-tint", bg_color="bg-red-50/30", icon_color="text-red-600",
                best_seller=False, rating=4, ideal_for="Natural cherry-bitten lip and cheek tinting",
                ingredients="Pomegranate Extract, Grapefruit Peel Extract, Vitamins",
                benefits="Fast-absorbing water tint that delivers a vivid cherry color instantly to both lips and cheeks.",
                image_url="images/7.jpg"
            ),
            Product(
                category="makeup", brand="Too Cool For School", name="Artclass By Rodin Shading",
                price=19.00, img_icon="fa-palette", bg_color="bg-stone-200/50", icon_color="text-stone-700",
                best_seller=True, rating=5, ideal_for="Contouring nose, jawline, and hairline",
                ingredients="Micro-fine pigments, Talc, Zinc Oxide",
                benefits="Korea's most beloved multi-shading palette designed to construct natural contour lines and shadows.",
                image_url="images/8.jpg"
            ),
            Product(
                category="makeup", brand="Amuse", name="Dew Jelly Vegan Cushion",
                price=30.00, img_icon="fa-cookie", bg_color="bg-amber-50/40", icon_color="text-amber-500",
                best_seller=False, rating=4, ideal_for="Clean, vegan, and hypoallergenic daily makeup",
                ingredients="Jelly essence 70%, Birch Sap, Peptides",
                benefits="Moisturizes skin from within, bouncy jelly texture stays firm on the face with absolute comfort.",
                 image_url="images/9.jpg"
            ),
            Product(
                category="makeup", brand="Dasique", name="Shadow Palette (Autumn Breeze)",
                price=34.00, img_icon="fa-table-cells-large", bg_color="bg-amber-100/30", icon_color="text-amber-700",
                best_seller=False, rating=5, ideal_for="Soft, daily warm-toned eyeshadow looks",
                ingredients="Premium silicon-coated powders, delicate pearl glitters",
                benefits="9 warm aesthetic shades of smooth mattes, shimmering glitters, and glowing metallics.",
                 image_url="images/10.jpg"
            ),

            # === HAIRCARE (10 Products) ===
            Product(
                category="haircare", brand="Kundal", name="Honey & Macadamia Hair Treatment",
                price=16.50, img_icon="fa-wind", bg_color="bg-purple-50/70", icon_color="text-purple-600",
                best_seller=False, rating=4, ideal_for="Damaged, dry, color-treated hair types",
                ingredients="Hydrolyzed Soy/Wheat Protein, Macadamia Seed Oil, Honey Extract",
                benefits="Deeply repairs damaged hair fibers, restoring silky textures and magnificent botanical scents.",
                image_url="images/11.png"
            ),
            Product(
                category="haircare", brand="Ryoe", name="Double Effector Black Shampoo",
                price=29.00, img_icon="fa-droplet-slash", bg_color="bg-stone-200", icon_color="text-stone-900",
                best_seller=True, rating=5, ideal_for="Gray hair coverage and anti-hair loss",
                ingredients="Ginseng Root Extract, Black Bean Extract, Camellia Oil",
                benefits="Gently darkens gray hair naturally over 3 weeks while strengthening hair roots with premium ginseng.",
                 image_url="images/12.jpg"

            ),
            Product(
                category="haircare", brand="Mise En Scene", name="Perfect Serum Original",
                price=15.00, img_icon="fa-bottle-droplet", bg_color="bg-amber-50/80", icon_color="text-amber-700",
                best_seller=True, rating=5, ideal_for="Frizzy, tangled, split-end hair profiles",
                ingredients="7 Golden Noble Oils (Argan, Camellia, Coconut, Jojoba, Olive, Marula, Apricot)",
                benefits="Clinically proven to improve hair strength, moisture, and softness, reducing split ends instantly.",
                image_url="images/13.jpg"

            ),
            Product(
                category="haircare", brand="Dr.FORHAIR", name="Folligen Silk Treatment",
                price=22.00, img_icon="fa-spa", bg_color="bg-stone-50", icon_color="text-rose-700",
                best_seller=False, rating=5, ideal_for="Thin hair experiencing extreme hair fall",
                ingredients="Folligen Complex™, Silk Amino Acids, Salicylic Acid",
                benefits="Treats the scalp and hair simultaneously, boosting root volume while softening parched strands.",
                image_url="images/14.jpg"

            ),
            Product(
                category="haircare", brand="Aromatica", name="Rosemary Scalp Scaling Shampoo",
                price=24.00, img_icon="fa-scissors", bg_color="bg-emerald-50/50", icon_color="text-emerald-700",
                best_seller=False, rating=4, ideal_for="Oily scalp with dandruff and build-ups",
                ingredients="Rosemary Leaf Oil, BHA (Salicylic Acid), Pine Extract",
                benefits="Gently exfoliates dead skin cells on the scalp, unclogs hair follicles, and reduces itchy dandruff.",
                 image_url="images/15.jpg"
            ),
            Product(
                category="haircare", brand="Lador", name="Perfect Hair Fill-Up Ampoule",
                price=18.00, img_icon="fa-bolt", bg_color="bg-blue-50/50", icon_color="text-blue-600",
                best_seller=True, rating=5, ideal_for="Extremely damaged, bleached, or dry hair",
                ingredients="Keratin, Collagen, Silk Proteins, Ceramides",
                benefits="A miracle liquid-to-cream hair clinic ampoule that delivers protein-packed nourishment to cuticles.",
                 image_url="images/16.webp"
            ),
            Product(
                category="haircare", brand="Daleaf", name="Better Root Hair Tonic",
                price=20.00, img_icon="fa-shower", bg_color="bg-emerald-50/30", icon_color="text-teal-600",
                best_seller=False, rating=4, ideal_for="Warm, irritated scalps causing hair loss",
                ingredients="Niacinamide, Panthenol, Peppermint Leaf Extract",
                benefits="Cools down scalp temperatures instantly, reducing sebum and promoting healthy hair root density.",
                image_url="images/17.jpg"
            ),
            Product(
                category="haircare", brand="Julyme", name="Perfume Hair Essence (Sunset Freesia)",
                price=16.00, img_icon="fa-spray-can", bg_color="bg-pink-50/50", icon_color="text-pink-600",
                best_seller=False, rating=4, ideal_for="Daily hair perfume and light hydration",
                ingredients="80% botanical extracts, luxury fragrance oils",
                benefits="A luxurious, non-greasy lotion essence that leaves your hair smelling divine like Jo Malone fragrances.",
                 image_url="images/18.jpg"
            ),
            Product(
                category="haircare", brand="Moremo", name="Water Treatment Miracle 10",
                price=26.00, img_icon="fa-stopwatch", bg_color="bg-rose-100/40", icon_color="text-rose-600",
                best_seller=True, rating=5, ideal_for="Busy mornings requiring rapid hair repair",
                ingredients="SR-21 Complex (3 kinds of keratin), Hydrolized Silk",
                benefits="An advanced water formula that heats up on wet hair, deeply repairing damaged hair in just 10 seconds.",
                image_url="images/19.jpg"
            ),
            Product(
                category="haircare", brand="CP-1", name="Premium Silk Protein Ampoule",
                price=14.00, img_icon="fa-syringe", bg_color="bg-amber-50/30", icon_color="text-amber-600",
                best_seller=False, rating=4, ideal_for="Split ends and heat-damaged hair",
                ingredients="Hydrolyzed Silk, Elasitn, Wheat Proteins",
                benefits="A leave-in protein treatment that coats hair strands to prevent damage from heat styling tools.",
                 image_url="images/20.jpg"
            ),

            # === PERFUME (10 Products) ===
            Product(
                category="perfume", brand="Tamburins", name="Chamo Solid Perfume Balm",
                price=42.00, img_icon="fa-shield-halved", bg_color="bg-stone-200/50", icon_color="text-stone-800",
                best_seller=True, rating=5, ideal_for="Niche, minimalist, and travel-friendly scent profiles",
                ingredients="Chamomile Extract, Sage Essence, Cedarwood Oils, White Musk",
                benefits="Spreads smoothly onto warm pulse points, leaving a beautiful aura of soft chamomile and musk.",
                image_url="images/21.jpg"
            ),
            Product(
                category="perfume", brand="Granhand", name="Susie Salmon Multi Perfume",
                price=38.00, img_icon="fa-wind", bg_color="bg-orange-50/40", icon_color="text-orange-600",
                best_seller=True, rating=5, ideal_for="Freshly-washed laundry scent fans",
                ingredients="Peach, Apple, Lily of the valley, White Musk",
                benefits="A refreshing, everyday scent that feels like wrapping yourself in clean laundry on a sunny morning.",
                 image_url="images/22.jpg"
            ),
            Product(
                category="perfume", brand="Nonfiction", name="Santal Cream Eau de Parfum",
                price=65.00, img_icon="fa-tree", bg_color="bg-stone-100", icon_color="text-green-800",
                best_seller=True, rating=5, ideal_for="Warm, woody, cozy scent lovers",
                ingredients="Sandalwood, Vetiver, Cardamom, Amber, Ginger",
                benefits="An exquisite, comforting combination of creamy sandalwood and fresh cardamom scent notes.",
                image_url="images/23.jpg"
            ),
            Product(
                category="perfume", brand="BorntoStandOut", name="Dirty Rice Eau de Parfum",
                price=95.00, img_icon="fa-fire", bg_color="bg-stone-50", icon_color="text-rose-900",
                best_seller=False, rating=5, ideal_for="Aesthetic, rebellious niche fragrance collectors",
                ingredients="Basmati Rice Accord, Almond, Milk, Sandalwood, Musk",
                benefits="A mesmerizing, skin-like and sensual fragrance depicting warm basmati rice with modern woody musk.",
                image_url="images/24.png"
            ),
            Product(
                category="perfume", brand="W.Dressroom", name="Dress & Living Clear Perfume No.97",
                price=12.00, img_icon="fa-feather", bg_color="bg-sky-50/60", icon_color="text-sky-600",
                best_seller=False, rating=4, ideal_for="Room, clothing, and body refreshing sprays",
                ingredients="Deodorizing properties, botanical aroma oils",
                benefits="The world-famous 'April Cotton' scent that neutralizes bad odors and spreads pure cotton freshness.",
                image_url="images/25.jpg"
            ),
            Product(
                category="perfume", brand="Cosmic Mansion", name="Full Moon Eau de Parfum",
                price=45.00, img_icon="fa-moon", bg_color="bg-indigo-50/40", icon_color="text-indigo-800",
                best_seller=False, rating=4, ideal_for="Evening wear and calming herbal experiences",
                ingredients="Lavender, Cedarwood, Peppermint, Sweet Bourbon",
                benefits="A calming, deep floral and herbal scent that evokes a quiet, starry night in a deep forest.",
                 image_url="images/26.jpg"
            ),
            Product(
                category="perfume", brand="Buly 1803", name="Eau Triple (Aladdin Edition)",
                price=110.00, img_icon="fa-gem", bg_color="bg-amber-100/40", icon_color="text-amber-800",
                best_seller=False, rating=5, ideal_for="Luxury collectors seeking water-based fragrances",
                ingredients="Water-based formulation, Orange blossom, Jasmine, Amber",
                benefits="An alcohol-free, water-based luxury perfume that smells heavenly and is extremely gentle on sensitive skin.",
                image_url="images/27.jpg"
            ),
            Product(
                category="perfume", brand="Pesade", name="In Hindsight Eau de Parfum",
                price=58.00, img_icon="fa-history", bg_color="bg-stone-200/40", icon_color="text-stone-700",
                best_seller=False, rating=4, ideal_for="Elegant, powdery, and musky aesthetics",
                ingredients="Raspberry, Peach, Rose, Musk, Patchouli",
                benefits="An elegant floral powdery scent with sweet hints of peach that captures beautiful nostalgia.",
                image_url="images/28.jpg"
            ),
            Product(
                category="perfume", brand="Celluver", name="Chiffon Perfume (Taylor)",
                price=18.00, img_icon="fa-shirt", bg_color="bg-purple-50/50", icon_color="text-purple-500",
                best_seller=False, rating=4, ideal_for="Daily, lightweight fabric and body misting",
                ingredients="Tulip, Freesia, Bergamot, Vetiver",
                benefits="A fresh, delicate fragrance capturing the aroma of a garden blooming with fresh, morning tulips.",
                image_url="images/29.jpg"
            ),
            Product(
                category="perfume", brand="A'ddict", name="Fever 314 Solid Perfume",
                price=34.00, img_icon="fa-thermometer", bg_color="bg-stone-50", icon_color="text-rose-500",
                best_seller=True, rating=5, ideal_for="Layering under traditional liquid perfumes",
                ingredients="Water-wrap silicon gel, Cedarwood, Leafy greens, Musk",
                benefits="An alcohol-free cream perfume that blends with your body's natural heat to create a completely unique scent.",
                image_url="images/30.jpg"
            )
        ]
        db.session.add_all(initial_products)
    
    db.session.commit()
    return "Database initialized with admin and 40 products! Please go to home page."

if __name__ == '__main__':
    app.run(debug=True)