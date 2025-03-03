#include <boost/bind.hpp>
#include <gazebo/physics/physics.hh>
#include <gazebo/common/common.hh>
#include <gazebo/transport/transport.hh>
#include <gazebo/msgs/msgs.hh>
#include <gazebo/gazebo.hh>

#include <iostream>
#include <stdio.h>

namespace gazebo
{
  class GripperPlugin : public ModelPlugin
  {

    // Pointer to the model
    private: physics::ModelPtr model;

    // Pointer to the update event connection
    private: event::ConnectionPtr updateConnection;
    private: transport::SubscriberPtr msgSubscriber;

    typedef const boost::shared_ptr<const gazebo::msgs::GzString> GzStringPtr;
    void cb(GzStringPtr &_msg)
    {
      // Dump the message contents to stdout.
      std::cout << _msg->DebugString();
    }

    public: void Load(physics::ModelPtr _parent, sdf::ElementPtr /*_sdf*/)
    {
      std::cout << "loading plugin" << std::endl;
      // Store the pointer to the model
      this->model = _parent;

      // Create our node for communication
      gazebo::transport::NodePtr node(new gazebo::transport::Node());
      node->Init("default");

      // Listen to custom topic
      msgSubscriber = node->Subscribe("/gazebo/default/gripperMsg", &GripperPlugin::cb, this); //, gazebo::msgs::Request, false);
      // Listen to the update event. This event is broadcast every
      // simulation iteration.
      //this->updateConnection = event::Events::ConnectWorldUpdateBegin(
        //  boost::bind(&ModelPush::OnUpdate, this, _1));


    }



    // Called by the world update start event
    public: void OnUpdate(const common::UpdateInfo & /*_info*/)
    {
      // Apply a small linear velocity to the model.
    }


  };

  // Register this plugin with the simulator
  GZ_REGISTER_MODEL_PLUGIN(GripperPlugin)
}
