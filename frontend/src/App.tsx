import React, { useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { RoleProvider } from './contexts/RoleContext';
import { ToastProvider, useToast } from './components/shared/Toast';
import { Spinner } from './components/shared/Spinner';
import { Sidebar } from './components/layout/Sidebar';
import { RoleSwitcher } from './components/layout/RoleSwitcher';
import { ChatInterface } from './components/chat/ChatInterface';
import { ContentManagement } from './components/admin/ContentManagement';
import { ContentApproval } from './components/admin/ContentApproval';
import { EscalationQueue } from './components/admin/EscalationQueue';
import { Analytics } from './components/admin/Analytics';
import { AuditLog } from './components/admin/AuditLog';
import { FaithfulnessReview } from './components/admin/FaithfulnessReview';
import { AdversarialReview } from './components/admin/AdversarialReview';
import { AccessRequestQueue } from './components/admin/AccessRequestQueue';
import { ResourceCatalogue } from './components/admin/ResourceCatalogue';
import { ActionManagement } from './components/admin/ActionManagement';
import { ConfigurationConsole } from './components/admin/ConfigurationConsole';
import { UserManagement } from './components/admin/UserManagement';
import { Login } from './components/auth/Login';
import type { Role } from './types';

const ROUTE_ACCESS: Record<string, Role[]> = {
  '/chat': ['employee', 'it_support_agent', 'it_content_owner', 'it_operations_lead', 'it_operations_manager', 'resource_owner', 'administrator', 'compliance_reviewer'],
  '/admin/content': ['it_content_owner', 'it_operations_manager', 'administrator'],
  '/admin/approvals': ['it_operations_lead', 'it_operations_manager', 'administrator'],
  '/admin/escalations': ['it_support_agent', 'it_operations_manager', 'administrator'],
  '/admin/analytics': ['it_operations_lead', 'it_operations_manager', 'administrator'],
  '/admin/audit': ['it_operations_manager', 'compliance_reviewer', 'administrator'],
  '/admin/faithfulness': ['it_operations_lead', 'compliance_reviewer', 'administrator'],
  '/admin/adversarial': ['it_operations_lead', 'administrator'],
  '/admin/access-requests': ['resource_owner', 'it_operations_lead', 'administrator'],
  '/admin/actions': ['it_operations_lead', 'administrator'],
  '/admin/resources': ['administrator'],
  '/admin/users': ['administrator'],
  '/admin/config': ['administrator'],
};

function LoadingScreen() {
  return (
    <div className="flex h-full items-center justify-center bg-gray-50">
      <Spinner size="lg" />
    </div>
  );
}

function ProtectedRoute({ path, children }: { path: string; children: React.ReactNode }) {
  const { currentUser, isAuthenticated, loading } = useAuth();
  const { showToast } = useToast();
  const navigate = useNavigate();
  const allowedRoles = ROUTE_ACCESS[path] ?? [];

  useEffect(() => {
    if (loading) return;
    if (!isAuthenticated) {
      showToast('Please login to access this page.', 'warning');
      navigate('/login', { replace: true });
      return;
    }
    if (currentUser && !allowedRoles.includes(currentUser.role)) {
      showToast('You do not have permission to access that page.', 'warning');
      navigate('/chat', { replace: true });
    }
  }, [loading, isAuthenticated, currentUser, allowedRoles, navigate, showToast]);

  if (loading) return <LoadingScreen />;
  if (!isAuthenticated || (currentUser && !allowedRoles.includes(currentUser.role))) return null;
  return <>{children}</>;
}

function DefaultRedirect() {
  const { currentUser, isAuthenticated, loading } = useAuth();

  if (loading) return <LoadingScreen />;
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  if (currentUser) {
    if (currentUser.role === 'compliance_reviewer') return <Navigate to="/admin/audit" replace />;
    return <Navigate to="/chat" replace />;
  }
  return <Navigate to="/login" replace />;
}

function AppShell() {
  return (
    <div className="flex flex-col h-screen bg-gray-50 overflow-hidden">
      <RoleSwitcher />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar />
        <div className="flex-1 overflow-hidden">
          <main className="h-full overflow-hidden flex flex-col">
          <Routes>
            <Route path="/" element={<DefaultRedirect />} />
            <Route path="/chat" element={
              <ProtectedRoute path="/chat">
                <ChatInterface />
              </ProtectedRoute>
            } />
            <Route path="/admin/content" element={
              <ProtectedRoute path="/admin/content">
                <ContentManagement />
              </ProtectedRoute>
            } />
            <Route path="/admin/approvals" element={
              <ProtectedRoute path="/admin/approvals">
                <ContentApproval />
              </ProtectedRoute>
            } />
            <Route path="/admin/escalations" element={
              <ProtectedRoute path="/admin/escalations">
                <EscalationQueue />
              </ProtectedRoute>
            } />
            <Route path="/admin/analytics" element={
              <ProtectedRoute path="/admin/analytics">
                <Analytics />
              </ProtectedRoute>
            } />
            <Route path="/admin/audit" element={
              <ProtectedRoute path="/admin/audit">
                <AuditLog />
              </ProtectedRoute>
            } />
            <Route path="/admin/faithfulness" element={
              <ProtectedRoute path="/admin/faithfulness">
                <FaithfulnessReview />
              </ProtectedRoute>
            } />
            <Route path="/admin/adversarial" element={
              <ProtectedRoute path="/admin/adversarial">
                <AdversarialReview />
              </ProtectedRoute>
            } />
            <Route path="/admin/access-requests" element={
              <ProtectedRoute path="/admin/access-requests">
                <AccessRequestQueue />
              </ProtectedRoute>
            } />
            <Route path="/admin/resources" element={
              <ProtectedRoute path="/admin/resources">
                <ResourceCatalogue />
              </ProtectedRoute>
            } />
            <Route path="/admin/actions" element={
              <ProtectedRoute path="/admin/actions">
                <ActionManagement />
              </ProtectedRoute>
            } />
            <Route path="/admin/config" element={
              <ProtectedRoute path="/admin/config">
                <ConfigurationConsole />
              </ProtectedRoute>
            } />
            <Route path="/admin/users" element={
              <ProtectedRoute path="/admin/users">
                <UserManagement />
              </ProtectedRoute>
            } />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
          </main>
        </div>
      </div>
    </div>
  );
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="*" element={
        <RoleProvider>
          <AppShell />
        </RoleProvider>
      } />
    </Routes>
  );
}

function AppWithRouter() {
  return (
    <AuthProvider>
      <ToastProvider>
        <AppRoutes />
      </ToastProvider>
    </AuthProvider>
  );
}

export default AppWithRouter;
