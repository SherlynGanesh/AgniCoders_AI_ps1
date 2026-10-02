export const catalog = [
  { id: 1, img: '/products/atta.jpg', name: 'Aashirvaad Atta', emoji: '🌾', unit: 'kg', price: 45, stock: 50, min: 10, sold: 120 },
  { id: 2, img: '/products/sugar.jpg', name: 'Sugar', emoji: '🍬', unit: 'kg', price: 48, stock: 18, min: 10, sold: 85 },
  { id: 3, img: '/products/butter.jpg', name: 'Amul Butter 100g', emoji: '🧈', unit: 'pc', price: 58, stock: 6, min: 10, sold: 64 },
  { id: 4, img: '/products/sunflower-oil.jpg', name: 'Sunflower Oil 1L', emoji: '🌻', unit: 'pc', price: 150, stock: 12, min: 5, sold: 48 },
  { id: 5, img: '/products/groundnut-oil.jpg', name: 'Groundnut Oil 1L', emoji: '🥜', unit: 'pc', price: 190, stock: 4, min: 5, sold: 33 },
  { id: 6, img: '/products/mustard-oil.jpg', name: 'Mustard Oil 1L', emoji: '🫒', unit: 'pc', price: 170, stock: 9, min: 5, sold: 27 },
  { id: 7, img: '/products/salt.jpg', name: 'Tata Salt 1kg', emoji: '🧂', unit: 'pc', price: 28, stock: 0, min: 10, sold: 40 },
  { id: 8, img: '/products/toor-dal.jpg', name: 'Toor Dal 1kg', emoji: '🫘', unit: 'kg', price: 160, stock: 22, min: 8, sold: 52 }];
export const orders = [
  { id: '#1042', customer: 'Sharma ji', date: 'Today', items: 3, total: 438, status: 'Confirmed' },
  { id: '#1041', customer: 'Mrs. Verma', date: 'Today', items: 2, total: 296, status: 'Awaiting reply' },
  { id: '#1040', customer: 'Anil Traders', date: 'Yesterday', items: 5, total: 1240, status: 'Confirmed' },
  { id: '#1039', customer: 'Pooja Joshi', date: 'Yesterday', items: 1, total: 190, status: 'Confirmed' }];
export const customers = [
  { id: 1, img: '/products/atta.jpg', name: 'Sharma ji', phone: '+91 98200 11111', orders: 24, spent: 9860, usual: 'Groundnut oil, Atta' },
  { id: 2, img: '/products/sugar.jpg', name: 'Mrs. Verma', phone: '+91 98200 22222', orders: 17, spent: 5410, usual: 'Sugar, Amul butter' },
  { id: 3, img: '/products/butter.jpg', name: 'Anil Traders', phone: '+91 98200 33333', orders: 41, spent: 38200, usual: 'Atta 25kg, Toor dal' },
  { id: 4, img: '/products/sunflower-oil.jpg', name: 'Pooja Joshi', phone: '+91 98200 44444', orders: 6, spent: 1320, usual: 'Mustard oil' }];
