import {createContext,useContext,useEffect,useState,type ReactNode} from 'react';
import {api,send} from '../api/http';
import type {User} from '../api/types';
type Auth={user:User|null;loading:boolean;setUser:(user:User|null)=>void;logout:()=>Promise<void>};
const Context=createContext<Auth>(null!);
export const useAuth=()=>useContext(Context);
export function AuthProvider({children}:{children:ReactNode}){
 const [user,setUser]=useState<User|null>(null),[loading,setLoading]=useState(true);
 useEffect(()=>{api<User>('/auth/me').then(setUser).catch(()=>{}).finally(()=>setLoading(false));const handler=()=>setUser(null);window.addEventListener('campus:unauthorized',handler);return()=>window.removeEventListener('campus:unauthorized',handler);},[]);
 const logout=async()=>{await send('/auth/logout',{});setUser(null);};
 return <Context.Provider value={{user,loading,setUser,logout}}>{children}</Context.Provider>;
}
