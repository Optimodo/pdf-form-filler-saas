import React from 'react';

const UserInfo = () => {
  // Demo data - in real app this would come from auth context
  const user = {
    name: "John D.",
    plan: "Pro",
    credits: 150
  };

  return (
    <div className="user-info">
      <span className="user-avatar">👤</span>
      <span className="user-details">
        {user.name} | {user.plan} | {user.credits} credits
      </span>
    </div>
  );
};

export default UserInfo;
