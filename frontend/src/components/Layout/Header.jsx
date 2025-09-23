import React from 'react';
import ThemeToggle from '../UI/ThemeToggle';
import UserInfo from '../User/UserInfo';

const Header = () => {
  return (
    <header className="header">
      <div className="header-left">
        <div className="logo">
          <span className="logo-icon">📄</span>
          <span className="logo-text">PDF Form Filler</span>
        </div>
      </div>
      
      <div className="header-right">
        <UserInfo />
        <ThemeToggle />
      </div>
    </header>
  );
};

export default Header;
