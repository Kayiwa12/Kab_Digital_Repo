/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 */

export default function App() {
  return (
    <div style={{
      fontFamily: 'system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      minHeight: '100vh',
      margin: 0,
      backgroundColor: '#f8fafc',
      color: '#0f172a',
      padding: '1.5rem',
      textAlign: 'center'
    }}>
      <div style={{
        maxWidth: '540px',
        backgroundColor: '#ffffff',
        padding: '2.5rem',
        borderRadius: '12px',
        boxShadow: '0 4px 20px -2px rgba(0, 0, 0, 0.08)',
        border: '1px solid #e2e8f0'
      }}>
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, color: '#047857', marginBottom: '0.75rem' }}>
          Kabale University Research Repository
        </h1>
        <p style={{ color: '#475569', fontSize: '0.95rem', lineHeight: 1.6, marginBottom: '1.5rem' }}>
          Research Discovery, Faculty Analytics & DSpace Indexing Platform.
        </p>
        <a
          href="/"
          style={{
            display: 'inline-block',
            backgroundColor: '#047857',
            color: '#ffffff',
            fontWeight: 600,
            padding: '0.75rem 1.5rem',
            borderRadius: '8px',
            textDecoration: 'none'
          }}
        >
          Enter Research Portal
        </a>
      </div>
    </div>
  );
}

