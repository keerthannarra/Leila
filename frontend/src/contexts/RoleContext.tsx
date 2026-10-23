import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { User, Role } from '../types';
import { api } from '../services/api';
import { useAuth } from './AuthContext';

const DEMO_USERS: User[] = [
  { id: 'u1', name: 'Alice Johnson', email: 'alice@company.com', role: 'employee', employment_type: 'full_time' },
  { id: 'u2', name: 'Bob Martinez', email: 'bob@company.com', role: 'it_support_agent', employment_type: 'full_time' },
  { id: 'u3', name: 'Carol Singh', email: 'carol@company.com', role: 'it_content_owner', employment_type: 'full_time' },
  { id: 'u4', name: 'David Kim', email: 'david@company.com', role: 'it_operations_lead', employment_type: 'full_time' },
  { id: 'u5', name: 'Eva Chen', email: 'eva@company.com', role: 'it_operations_manager', employment_type: 'full_time' },
  { id: 'u6', name: 'Frank Liu', email: 'frank@company.com', role: 'resource_owner', employment_type: 'full_time' },
  { id: 'u7', name: 'Grace Park', email: 'grace@company.com', role: 'administrator', employment_type: 'full_time' },
  { id: 'u8', name: 'Henry Walsh', email: 'henry@company.com', role: 'compliance_reviewer', employment_type: 'full_time' },
];

interface RoleContextType {
  currentUser: User;
  setCurrentUser: (user: User) => void;
  currentRole: Role;
  availableUsers: User[];
  switchRole: (userId: string) => void;
}

const RoleContext = createContext<RoleContextType | null>(null);

export function RoleProvider({ children }: { children: React.ReactNode }) {
  const { currentUser: authUser } = useAuth();
  const [availableUsers, setAvailableUsers] = useState<User[]>(DEMO_USERS);
  const [currentUser, setCurrentUserState] = useState<User>(authUser ?? DEMO_USERS[0]);

  // Keep currentUser in sync with the authenticated user
  useEffect(() => {
    if (authUser) {
      setCurrentUserState(authUser);
    }
  }, [authUser]);

  useEffect(() => {
    api.users.list().then(users => {
      if (users && users.length > 0) {
        setAvailableUsers(users);
      }
    }).catch(() => {
      // backend not available — use demo users
    });
  }, []);

  const setCurrentUser = useCallback((user: User) => {
    setCurrentUserState(user);
  }, []);

  const switchRole = useCallback((userId: string) => {
    const user = availableUsers.find(u => u.id === userId);
    if (user) {
      setCurrentUser(user);
    }
  }, [availableUsers, setCurrentUser]);

  return (
    <RoleContext.Provider
      value={{
        currentUser,
        setCurrentUser,
        currentRole: currentUser.role,
        availableUsers,
        switchRole,
      }}
    >
      {children}
    </RoleContext.Provider>
  );
}

export function useRole() {
  const ctx = useContext(RoleContext);
  if (!ctx) throw new Error('useRole must be used within RoleProvider');
  return ctx;
}
