import requests
import sys
import json
from datetime import datetime

class HairEcommerceAPITester:
    def __init__(self, base_url="https://8b8e84f7-cfb1-407d-9593-ba52e7915182.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.created_product_id = None

    def run_test(self, name, method, endpoint, expected_status, data=None, params=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        print(f"   URL: {url}")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, params=params)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    response_data = response.json()
                    if isinstance(response_data, dict) and len(str(response_data)) < 500:
                        print(f"   Response: {response_data}")
                    elif isinstance(response_data, list):
                        print(f"   Response: List with {len(response_data)} items")
                except:
                    print(f"   Response: {response.text[:200]}...")
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"   Response: {response.text[:300]}")

            return success, response.json() if response.text and response.status_code < 500 else {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_init_data(self):
        """Initialize sample data"""
        success, response = self.run_test(
            "Initialize Sample Data",
            "POST",
            "init-data",
            200
        )
        return success

    def test_get_products(self):
        """Test getting all products"""
        success, response = self.run_test(
            "Get All Products",
            "GET",
            "products",
            200
        )
        if success and isinstance(response, list) and len(response) > 0:
            self.created_product_id = response[0].get('id')
            print(f"   Found {len(response)} products")
            return True
        return success

    def test_get_products_by_category(self):
        """Test getting products by category"""
        categories = ['extensions', 'wigs', 'bundles', 'hair_care', 'accessories']
        for category in categories:
            success, response = self.run_test(
                f"Get Products - {category}",
                "GET",
                "products",
                200,
                params={'category': category}
            )
            if not success:
                return False
        return True

    def test_get_single_product(self):
        """Test getting a single product"""
        if not self.created_product_id:
            print("❌ No product ID available for single product test")
            return False
            
        success, response = self.run_test(
            "Get Single Product",
            "GET",
            f"products/{self.created_product_id}",
            200
        )
        return success

    def test_register_user(self):
        """Test user registration"""
        timestamp = datetime.now().strftime('%H%M%S')
        user_data = {
            "email": f"testuser{timestamp}@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "password": "testpass123"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=user_data
        )
        
        if success and 'id' in response:
            self.user_id = response['id']
            # Store user data for login test
            self.test_email = user_data['email']
            self.test_password = user_data['password']
            return True
        return success

    def test_login_user(self):
        """Test user login"""
        if not hasattr(self, 'test_email'):
            print("❌ No user credentials available for login test")
            return False
            
        login_data = {
            "email": self.test_email,
            "password": self.test_password
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            print(f"   Token received: {self.token[:20]}...")
            return True
        return success

    def test_get_current_user(self):
        """Test getting current user info"""
        if not self.token:
            print("❌ No token available for current user test")
            return False
            
        success, response = self.run_test(
            "Get Current User",
            "GET",
            "auth/me",
            200
        )
        return success

    def test_get_cart(self):
        """Test getting user cart"""
        if not self.token:
            print("❌ No token available for cart test")
            return False
            
        success, response = self.run_test(
            "Get User Cart",
            "GET",
            "cart",
            200
        )
        return success

    def test_add_to_cart(self):
        """Test adding item to cart"""
        if not self.token or not self.created_product_id:
            print("❌ No token or product ID available for add to cart test")
            return False
            
        success, response = self.run_test(
            "Add Item to Cart",
            "POST",
            "cart/add",
            200,
            params={'product_id': self.created_product_id, 'quantity': 2}
        )
        return success

    def test_remove_from_cart(self):
        """Test removing item from cart"""
        if not self.token or not self.created_product_id:
            print("❌ No token or product ID available for remove from cart test")
            return False
            
        success, response = self.run_test(
            "Remove Item from Cart",
            "DELETE",
            f"cart/remove/{self.created_product_id}",
            200
        )
        return success

    def test_invalid_endpoints(self):
        """Test invalid endpoints return proper errors"""
        # Test non-existent product
        success, response = self.run_test(
            "Get Non-existent Product",
            "GET",
            "products/invalid-id",
            404
        )
        
        # Test invalid login
        invalid_login = {
            "email": "invalid@example.com",
            "password": "wrongpassword"
        }
        success2, response2 = self.run_test(
            "Invalid Login",
            "POST",
            "auth/login",
            401,
            data=invalid_login
        )
        
        return success and success2

def main():
    print("🚀 Starting Hair Ecommerce API Tests")
    print("=" * 50)
    
    # Setup
    tester = HairEcommerceAPITester()
    
    # Run tests in sequence
    test_sequence = [
        ("Initialize Sample Data", tester.test_init_data),
        ("Get All Products", tester.test_get_products),
        ("Get Products by Category", tester.test_get_products_by_category),
        ("Get Single Product", tester.test_get_single_product),
        ("User Registration", tester.test_register_user),
        ("User Login", tester.test_login_user),
        ("Get Current User", tester.test_get_current_user),
        ("Get User Cart", tester.test_get_cart),
        ("Add to Cart", tester.test_add_to_cart),
        ("Remove from Cart", tester.test_remove_from_cart),
        ("Invalid Endpoints", tester.test_invalid_endpoints),
    ]
    
    print(f"\n📋 Running {len(test_sequence)} test suites...")
    
    for test_name, test_func in test_sequence:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            if not result:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {str(e)}")
    
    # Print final results
    print(f"\n{'='*50}")
    print(f"📊 FINAL RESULTS")
    print(f"{'='*50}")
    print(f"Tests Run: {tester.tests_run}")
    print(f"Tests Passed: {tester.tests_passed}")
    print(f"Tests Failed: {tester.tests_run - tester.tests_passed}")
    print(f"Success Rate: {(tester.tests_passed/tester.tests_run)*100:.1f}%")
    
    if tester.tests_passed == tester.tests_run:
        print("🎉 All tests passed!")
        return 0
    else:
        print("⚠️  Some tests failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())