import http from './http'
export const getNetwork=(q='')=>http.get('/startup/network',{params:{q}}).then(r=>r.data)
export const connectFounder=id=>http.post(`/startup/network/connect/${id}`).then(r=>r.data)
export const acceptConnection=id=>http.patch(`/startup/network/connections/${id}`,{}).then(r=>r.data)
export const removeConnection=id=>http.delete(`/startup/network/connections/${id}`).then(r=>r.data)
export const getMessages=id=>http.get(`/startup/network/connections/${id}/messages`).then(r=>r.data)
export const sendMessage=(id,text)=>http.post(`/startup/network/connections/${id}/messages`,{text}).then(r=>r.data)
export const getPosts=()=>http.get('/startup/network/posts').then(r=>r.data)
export const createPost=payload=>http.post('/startup/network/posts',payload).then(r=>r.data)
export const deletePost=id=>http.delete(`/startup/network/posts/${id}`).then(r=>r.data)
export const uploadPostImage=(id,file)=>{const data=new FormData();data.append('image',file);return http.post(`/startup/network/posts/${id}`,data).then(r=>r.data)}
export const recommendFounders=()=>http.post('/startup/network/recommendations').then(r=>r.data)
