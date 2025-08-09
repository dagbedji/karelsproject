import React, { useState, useEffect, useContext, createContext } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import axios from 'axios';
import { Toaster } from './components/ui/toaster';
import { toast } from './hooks/use-toast';
import { Button } from './components/ui/button';
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from './components/ui/card';
import { Input } from './components/ui/input';
import { Badge } from './components/ui/badge';
import { Separator } from './components/ui/separator';
import { Avatar, AvatarFallback, AvatarImage } from './components/ui/avatar';
import { 
  ShoppingCart, 
  Heart, 
  Search, 
  User, 
  Menu, 
  Star, 
  Plus, 
  Minus, 
  X,
  Package,
  CreditCard,
  MapPin,
  Phone,
  Mail,
  Instagram,
  Facebook,
  Twitter
} from 'lucide-react';
import './App.css';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

// Auth Context
const AuthContext = createContext();
const useAuth = () => useContext(AuthContext);

// Cart Context  
const CartContext = createContext();
const useCart = () => useContext(CartContext);

// Auth Provider
const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchUser = async () => {
    try {
      const response = await axios.get(`${API}/auth/me`);
      setUser(response.data);
    } catch (error) {
      localStorage.removeItem('token');
      delete axios.defaults.headers.common['Authorization'];
    } finally {
      setLoading(false);
    }
  };

  const login = async (email, password) => {
    try {
      const response = await axios.post(`${API}/auth/login`, { email, password });
      const { access_token, user } = response.data;
      localStorage.setItem('token', access_token);
      axios.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setUser(user);
      toast({ title: "Welcome back!", description: "You've been logged in successfully." });
      return true;
    } catch (error) {
      toast({ title: "Login failed", description: error.response?.data?.detail || "Invalid credentials", variant: "destructive" });
      return false;
    }
  };

  const register = async (userData) => {
    try {
      const response = await axios.post(`${API}/auth/register`, userData);
      toast({ title: "Account created!", description: "Please log in to continue." });
      return true;
    } catch (error) {
      toast({ title: "Registration failed", description: error.response?.data?.detail || "Failed to create account", variant: "destructive" });
      return false;
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
    toast({ title: "Logged out", description: "You've been logged out successfully." });
  };

  return (
    <AuthContext.Provider value={{ user, login, register, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
};

// Cart Provider
const CartProvider = ({ children }) => {
  const [cart, setCart] = useState({ items: [], total_amount: 0 });
  const [cartOpen, setCartOpen] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    if (user) {
      fetchCart();
    }
  }, [user]);

  const fetchCart = async () => {
    try {
      const response = await axios.get(`${API}/cart`);
      setCart(response.data);
    } catch (error) {
      console.error('Failed to fetch cart:', error);
    }
  };

  const addToCart = async (productId, quantity = 1) => {
    try {
      await axios.post(`${API}/cart/add?product_id=${productId}&quantity=${quantity}`);
      await fetchCart();
      toast({ title: "Added to cart!", description: "Item has been added to your cart." });
    } catch (error) {
      toast({ title: "Error", description: "Failed to add item to cart", variant: "destructive" });
    }
  };

  const removeFromCart = async (productId) => {
    try {
      await axios.delete(`${API}/cart/remove/${productId}`);
      await fetchCart();
      toast({ title: "Removed", description: "Item removed from cart." });
    } catch (error) {
      toast({ title: "Error", description: "Failed to remove item", variant: "destructive" });
    }
  };

  return (
    <CartContext.Provider value={{ cart, addToCart, removeFromCart, cartOpen, setCartOpen }}>
      {children}
    </CartContext.Provider>
  );
};

// Header Component
const Header = ({ onAuthClick }) => {
  const { user, logout } = useAuth();
  const { cart, cartOpen, setCartOpen } = useCart();
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <header className="sticky top-0 z-50 w-full border-b bg-white/95 backdrop-blur supports-[backdrop-filter]:bg-white/60">
      <div className="container flex h-16 items-center justify-between px-4">
        <div className="flex items-center space-x-4">
          <h1 className="text-2xl font-bold bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            HairGlow
          </h1>
        </div>
        
        <div className="flex-1 max-w-lg mx-8">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
            <Input 
              placeholder="Search products..." 
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-10"
            />
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setCartOpen(true)}
            className="relative"
          >
            <ShoppingCart className="h-5 w-5" />
            {cart.items.length > 0 && (
              <Badge className="absolute -top-2 -right-2 h-5 w-5 flex items-center justify-center text-xs">
                {cart.items.length}
              </Badge>
            )}
          </Button>
          
          {user ? (
            <div className="flex items-center space-x-2">
              <Avatar>
                <AvatarFallback>{user.first_name[0]}{user.last_name[0]}</AvatarFallback>
              </Avatar>
              <Button variant="outline" size="sm" onClick={logout}>
                Logout
              </Button>
            </div>
          ) : (
            <Button size="sm" onClick={() => onAuthClick('login')}>Sign In</Button>
          )}
        </div>
      </div>
    </header>
  );
};

// Product Card Component
const ProductCard = ({ product }) => {
  const { addToCart } = useCart();
  const { user } = useAuth();

  return (
    <Card className="group overflow-hidden hover:shadow-lg transition-shadow duration-300">
      <div className="aspect-square overflow-hidden">
        <img
          src={product.images[0]}
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
        />
      </div>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <Badge variant="secondary" className="mb-2">
            {product.category.replace('_', ' ').toUpperCase()}
          </Badge>
          <Button variant="ghost" size="icon">
            <Heart className="h-4 w-4" />
          </Button>
        </div>
        <CardTitle className="text-lg line-clamp-2">{product.name}</CardTitle>
      </CardHeader>
      <CardContent className="pt-0">
        <p className="text-gray-600 text-sm line-clamp-2 mb-3">{product.description}</p>
        <div className="flex items-center space-x-2 mb-3">
          <div className="flex text-yellow-400">
            {[...Array(5)].map((_, i) => (
              <Star key={i} className="h-4 w-4 fill-current" />
            ))}
          </div>
          <span className="text-sm text-gray-500">(4.8)</span>
        </div>
        <div className="flex items-center space-x-2">
          {Object.entries(product.attributes).slice(0, 2).map(([key, value]) => (
            <Badge key={key} variant="outline" className="text-xs">
              {value}
            </Badge>
          ))}
        </div>
      </CardContent>
      <CardFooter className="flex items-center justify-between">
        <div className="flex flex-col">
          <span className="text-2xl font-bold">${product.price}</span>
          <span className="text-xs text-gray-500">{product.stock_quantity} in stock</span>
        </div>
        <Button 
          onClick={() => user ? addToCart(product.id) : toast({ title: "Please login", description: "You need to login to add items to cart" })}
          className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700"
        >
          Add to Cart
        </Button>
      </CardFooter>
    </Card>
  );
};

// Home Component
const Home = ({ onAuthClick }) => {
  const [products, setProducts] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchProducts();
    initializeData();
  }, []);

  const fetchProducts = async (category = '') => {
    try {
      const response = await axios.get(`${API}/products${category ? `?category=${category}` : ''}`);
      setProducts(response.data);
    } catch (error) {
      toast({ title: "Error", description: "Failed to fetch products", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  };

  const initializeData = async () => {
    try {
      await axios.post(`${API}/init-data`);
    } catch (error) {
      console.log('Sample data already exists or failed to initialize');
    }
  };

  const categories = [
    { key: '', label: 'All Products' },
    { key: 'extensions', label: 'Extensions' },
    { key: 'wigs', label: 'Wigs' },
    { key: 'bundles', label: 'Bundles' },
    { key: 'hair_care', label: 'Hair Care' },
    { key: 'accessories', label: 'Accessories' },
  ];

  const handleCategoryChange = (category) => {
    setSelectedCategory(category);
    fetchProducts(category);
  };

  return (
    <div>
      {/* Hero Section */}
      <section className="relative min-h-[70vh] flex items-center justify-center overflow-hidden bg-gradient-to-br from-purple-50 to-pink-50">
        <div className="container px-4 py-20 text-center relative z-10">
          <h1 className="text-5xl md:text-7xl font-bold mb-6 bg-gradient-to-r from-purple-600 to-pink-600 bg-clip-text text-transparent">
            Transform Your Look
          </h1>
          <p className="text-xl md:text-2xl text-gray-600 mb-8 max-w-3xl mx-auto">
            Discover premium hair extensions, wigs, and accessories that enhance your natural beauty
          </p>
          <Button 
            size="lg" 
            className="bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-700 hover:to-pink-700 text-lg px-8 py-6"
            onClick={() => document.getElementById('products').scrollIntoView({ behavior: 'smooth' })}
          >
            Shop Collection
          </Button>
        </div>
        <div className="absolute inset-0 opacity-20">
          <img
            src="https://images.unsplash.com/photo-1500917293891-ef795e70e1f6?crop=entropy&cs=srgb&fm=jpg&ixid=M3w3NDk1NzZ8MHwxfHNlYXJjaHwxfHxoYWlyJTIwZXh0ZW5zaW9uc3xlbnwwfHx8fDE3NTQ3ODM1NTB8MA&ixlib=rb-4.1.0&q=85"
            alt="Hero"
            className="w-full h-full object-cover"
          />
        </div>
      </section>

      {/* Categories */}
      <section className="py-12 bg-gray-50">
        <div className="container px-4">
          <h2 className="text-3xl font-bold text-center mb-8">Shop by Category</h2>
          <div className="flex flex-wrap justify-center gap-4 mb-8">
            {categories.map((category) => (
              <Button
                key={category.key}
                variant={selectedCategory === category.key ? "default" : "outline"}
                onClick={() => handleCategoryChange(category.key)}
                className={selectedCategory === category.key ? "bg-gradient-to-r from-purple-600 to-pink-600" : ""}
              >
                {category.label}
              </Button>
            ))}
          </div>
        </div>
      </section>

      {/* Products */}
      <section id="products" className="py-16">
        <div className="container px-4">
          <h2 className="text-3xl font-bold text-center mb-12">Featured Products</h2>
          {loading ? (
            <div className="flex justify-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-8">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
};

// Cart Sidebar Component
const CartSidebar = () => {
  const { cart, cartOpen, setCartOpen, removeFromCart } = useCart();

  return (
    <div className={`fixed inset-0 z-50 ${cartOpen ? 'block' : 'hidden'}`}>
      <div className="absolute inset-0 bg-black/50" onClick={() => setCartOpen(false)} />
      <div className="absolute right-0 top-0 h-full w-96 bg-white shadow-xl">
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="text-lg font-semibold">Shopping Cart</h2>
          <Button variant="ghost" size="icon" onClick={() => setCartOpen(false)}>
            <X className="h-5 w-5" />
          </Button>
        </div>
        
        <div className="p-4 flex-1 overflow-y-auto">
          {cart.items.length === 0 ? (
            <p className="text-center text-gray-500 mt-8">Your cart is empty</p>
          ) : (
            <div className="space-y-4">
              {cart.items.map((item, index) => (
                <div key={index} className="flex items-center space-x-4 border rounded-lg p-3">
                  <div className="flex-1">
                    <h3 className="font-medium">Product #{item.product_id.slice(0, 8)}</h3>
                    <p className="text-sm text-gray-600">Qty: {item.quantity}</p>
                    <p className="font-semibold">${item.price}</p>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => removeFromCart(item.product_id)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              ))}
            </div>
          )}
        </div>
        
        {cart.items.length > 0 && (
          <div className="border-t p-4">
            <div className="flex justify-between items-center mb-4">
              <span className="font-semibold">Total: ${cart.total_amount?.toFixed(2)}</span>
            </div>
            <Button className="w-full bg-gradient-to-r from-purple-600 to-pink-600">
              Checkout
            </Button>
          </div>
        )}
      </div>
    </div>
  );
};

// Auth Modal Component
const AuthModal = ({ isOpen, onClose, mode, setMode }) => {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    first_name: '',
    last_name: ''
  });
  const { login, register } = useAuth();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (mode === 'login') {
      const success = await login(formData.email, formData.password);
      if (success) onClose();
    } else {
      const success = await register(formData);
      if (success) setMode('login');
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <Card className="relative w-96 mx-4">
        <CardHeader>
          <CardTitle>{mode === 'login' ? 'Sign In' : 'Create Account'}</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {mode === 'register' && (
              <>
                <Input
                  placeholder="First Name"
                  value={formData.first_name}
                  onChange={(e) => setFormData({...formData, first_name: e.target.value})}
                  required
                />
                <Input
                  placeholder="Last Name"
                  value={formData.last_name}
                  onChange={(e) => setFormData({...formData, last_name: e.target.value})}
                  required
                />
              </>
            )}
            <Input
              type="email"
              placeholder="Email"
              value={formData.email}
              onChange={(e) => setFormData({...formData, email: e.target.value})}
              required
            />
            <Input
              type="password"
              placeholder="Password"
              value={formData.password}
              onChange={(e) => setFormData({...formData, password: e.target.value})}
              required
            />
            <Button type="submit" className="w-full">
              {mode === 'login' ? 'Sign In' : 'Create Account'}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="flex-col space-y-2">
          <Button
            variant="link"
            onClick={() => setMode(mode === 'login' ? 'register' : 'login')}
          >
            {mode === 'login' ? 'Need an account? Sign up' : 'Already have an account? Sign in'}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

// Footer Component
const Footer = () => {
  return (
    <footer className="bg-gray-900 text-white py-16">
      <div className="container px-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <h3 className="text-2xl font-bold mb-4 bg-gradient-to-r from-purple-400 to-pink-400 bg-clip-text text-transparent">
              HairGlow
            </h3>
            <p className="text-gray-400 mb-4">
              Premium hair products for your beauty transformation journey.
            </p>
            <div className="flex space-x-4">
              <Facebook className="h-5 w-5 text-gray-400 hover:text-white cursor-pointer" />
              <Instagram className="h-5 w-5 text-gray-400 hover:text-white cursor-pointer" />
              <Twitter className="h-5 w-5 text-gray-400 hover:text-white cursor-pointer" />
            </div>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Categories</h4>
            <ul className="space-y-2 text-gray-400">
              <li>Hair Extensions</li>
              <li>Wigs</li>
              <li>Bundles</li>
              <li>Hair Care</li>
              <li>Accessories</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Customer Service</h4>
            <ul className="space-y-2 text-gray-400">
              <li>Contact Us</li>
              <li>Shipping Info</li>
              <li>Returns</li>
              <li>Size Guide</li>
              <li>Care Instructions</li>
            </ul>
          </div>
          
          <div>
            <h4 className="font-semibold mb-4">Contact</h4>
            <div className="space-y-2 text-gray-400">
              <div className="flex items-center space-x-2">
                <Mail className="h-4 w-4" />
                <span>support@hairglow.com</span>
              </div>
              <div className="flex items-center space-x-2">
                <Phone className="h-4 w-4" />
                <span>1-800-HAIR-GLOW</span>
              </div>
              <div className="flex items-center space-x-2">
                <MapPin className="h-4 w-4" />
                <span>New York, NY</span>
              </div>
            </div>
          </div>
        </div>
        
        <Separator className="my-8 bg-gray-800" />
        
        <div className="text-center text-gray-400">
          <p>&copy; 2024 HairGlow. All rights reserved.</p>
        </div>
      </div>
    </footer>
  );
};

// Main App Component
function App() {
  const [authModal, setAuthModal] = useState({ isOpen: false, mode: 'login' });

  const handleAuthClick = (mode) => {
    setAuthModal({ isOpen: true, mode });
  };

  return (
    <AuthProvider>
      <CartProvider>
        <Router>
          <div className="min-h-screen flex flex-col">
            <Header onAuthClick={handleAuthClick} />
            <main className="flex-1">
              <Routes>
                <Route path="/" element={<Home onAuthClick={handleAuthClick} />} />
              </Routes>
            </main>
            <Footer />
            <CartSidebar />
            <AuthModal
              isOpen={authModal.isOpen}
              onClose={() => setAuthModal({ ...authModal, isOpen: false })}
              mode={authModal.mode}
              setMode={(mode) => setAuthModal({ ...authModal, mode })}
            />
          </div>
          <Toaster />
        </Router>
      </CartProvider>
    </AuthProvider>
  );
}

export default App;