// "My Startup" — profile, onboarding, finance summary, and the founder's
// workspace blocks (employees, products, employee task assignments, to-dos).
import http from '@/api/http'

export function getStartupSummary() {
  return http.get('/startup/summary').then((r) => r.data)
}

export function getStartupProfile() {
  return http.get('/startup/profile').then((r) => r.data)
}

export function updateStartupProfile(payload) {
  return http.put('/startup/profile', payload).then((r) => r.data)
}

// Answers the five intake questions → AI writes an assessment and recommends
// which blocks to surface. Marks the profile onboarded.
export function submitStartupOnboarding(answers,language='en') {
  return http.post('/startup/onboarding', { answers,language }).then((r) => r.data)
}

// --- employees -------------------------------------------------------------
export function listEmployees() {
  return http.get('/startup/employees').then((r) => r.data)
}

export function createEmployee(payload) {
  return http.post('/startup/employees', payload).then((r) => r.data)
}

export function updateEmployee(id, payload) {
  return http.put(`/startup/employees/${id}`, payload).then((r) => r.data)
}

export function deleteEmployee(id) {
  return http.delete(`/startup/employees/${id}`).then((r) => r.data)
}

export function uploadEmployeePhoto(id, file) {
  const form = new FormData()
  form.append('photo', file)
  return http.post(`/startup/employees/${id}/photo`, form).then((r) => r.data)
}

// --- products --------------------------------------------------------------
export function listProducts() {
  return http.get('/startup/products').then((r) => r.data)
}

export function createProduct(payload) {
  return http.post('/startup/products', payload).then((r) => r.data)
}

export function updateProduct(id, payload) {
  return http.put(`/startup/products/${id}`, payload).then((r) => r.data)
}

export function deleteProduct(id) {
  return http.delete(`/startup/products/${id}`).then((r) => r.data)
}

export function uploadProductImage(id, file) {
  const form = new FormData()
  form.append('image', file)
  return http.post(`/startup/products/${id}/image`, form).then((r) => r.data)
}

// --- assignments (task dashboard) ------------------------------------------
export function listAssignments() {
  return http.get('/startup/assignments').then((r) => r.data)
}

export function createAssignment(payload) {
  return http.post('/startup/assignments', payload).then((r) => r.data)
}

export function updateAssignment(id, payload) {
  return http.patch(`/startup/assignments/${id}`, payload).then((r) => r.data)
}

export function deleteAssignment(id) {
  return http.delete(`/startup/assignments/${id}`).then((r) => r.data)
}

// --- startup to-dos --------------------------------------------------------
export function listStartupTodos() {
  return http.get('/startup/todos').then((r) => r.data)
}

export function createStartupTodo(title) {
  return http.post('/startup/todos', { title }).then((r) => r.data)
}

export function updateStartupTodo(id, payload) {
  return http.patch(`/startup/todos/${id}`, payload).then((r) => r.data)
}

export function deleteStartupTodo(id) {
  return http.delete(`/startup/todos/${id}`).then((r) => r.data)
}

// --- bulk import -------------------------------------------------------------
// Rows are parsed from the founder's CSV/JSON file in the browser (see
// utils/tableImport.js); the server validates every row and saves all or none.
export function importEmployees(rows) {
  return http.post('/startup/employees/import', { rows }).then((r) => r.data)
}

export function importProducts(rows) {
  return http.post('/startup/products/import', { rows }).then((r) => r.data)
}

// --- roadmap ---------------------------------------------------------------
// The road from where the startup stands to a full startup, walked like the
// study map. Questions first (the AI asks what it cannot tell from the
// records), then the build with the answers.
export function getRoadmap() {
  return http.get('/startup/roadmap').then((r) => r.data)
}

export function askRoadmapQuestions(language = 'en', answers) {
  return http.post('/startup/roadmap/questions', answers ? { language, answers } : { language }).then((r) => r.data)
}

export function buildRoadmap(language = 'en', answers) {
  return http.post('/startup/roadmap', answers ? { language, answers } : { language }).then((r) => r.data)
}

// Finish the next step or milestone ({done: true, note}) or reopen the latest one.
export function setRoadmapItem(id, payload) {
  return http.patch(`/startup/roadmap/items/${id}`, payload).then((r) => r.data)
}
